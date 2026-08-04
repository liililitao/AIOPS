"""
多模型对比测试 — 验证问题出在「提供商」还是「中转站」
=====================================================
3 个模型 × 4 种场景 × 3 轮连续调用 = 36 次请求
"""
import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Optional

from langchain_openai import ChatOpenAI

# ==================== 中转站配置 ====================
BASE_URL = "https://api.marketplace.novo-genai.com/v1"
API_KEY = os.getenv("LLM_API_KEY", "")

# ==================== 被测模型 ====================
MODELS = {
    "GPT5-Luna (OpenAI Azure)": "openai_gpt56_luna",
    "Gemini-Flash (Google Cloud)": "gemini_3_5_flash",
    "Qwen-VL (AWS)": "qwen_qwen3_vl_235b_a22b",
}

# ==================== 测试场景 ====================

# 场景1：极简 Prompt
SCENE1_SYS = "You are a helpful assistant."
SCENE1_USER = "Say OK"

# 场景2：中文运维角色 + 小 JSON
SCENE2_SYS = "你是一位资深的网络安全运维专家。请根据以下告警数据生成分析。"
SCENE2_USER = json.dumps({
    "alert_name": "WAF SQL Injection",
    "event_count": 150,
    "results": [{"properties_hostname": "test.example.com", "properties_action": "Blocked"}],
}, ensure_ascii=False)

# 场景3：完整生产 System Prompt（和 report_service.py 一样）
SCENE3_SYS = """你是一位资深的网络安全运维专家。请根据以下告警数据和 CMDB 资产信息，生成一份专业的 WAF 告警分析报告。

报告要求:
1. 使用 Markdown 格式
2. 包含以下章节:
   - 告警概要 (告警名称、触发时间、风险等级)
   - 告警数据详情 (受影响资源、攻击路径、WAF动作)
   - CMDB 资产信息 (证据溯源，附 CMDB 查询方式和结果)
   - 攻击分析 (攻击类型分类、攻击特征、风险评估)
   - 综合风险评估 (三维度判定详情)
   - 相关运维参考
3. 对于 CMDB 查询结果和攻击分类结果，必须在报告中标注为【证据溯源】
4. 语言专业、客观、准确
5. 在 Splunk 中查看的原始链接必须保留"""

# 场景4：完整生产 User Prompt（模拟真实告警，~5KB JSON）
SCENE4_SYS = SCENE3_SYS  # same system prompt
SCENE4_USER = """请根据以下信息生成 WAF 告警分析报告:

## 告警数据
{}

## CMDB 查询结果
{}

## 风险判定
{}

## 攻击类型分析
{}

请开始生成报告。""".format(
    json.dumps({
        "alert_name": "test-waf",
        "trigger_time": "2026-07-13T14:44:09.765+08:00",
        "event_count": 1,
        "splunk_url": "http://vm-cdcshared-tst-spl9forwarder:8000/app/search/search?q=...",
        "results": [{
            "id": "AGW-DAP-PRD-N3-01",
            "properties_hostname": "purview.novonordiskchina.com.cn",
            "properties_requestUri": "/.env.local /.env.production.local /admin/.env /app/.env /application/.env /conf/.env /crm/.env /cron/.env /development/.env /env.backup /laravel/core/.env /local/.env /node_modules/.env /prod/.env /public/.env /website/.env",
            "properties_action": "Blocked",
            "count": "20",
        }],
    }, ensure_ascii=False, indent=2),
    json.dumps({
        "found": True, "match_type": "exact", "resource_name": "AGW-DAP-PRD-N3-01",
        "resource_type": "Application gateway", "environment": "Production",
        "subscription": "DAP-PRD", "source_sheet": "Azure PaaS", "source_row": 283,
    }, ensure_ascii=False, indent=2),
    json.dumps({
        "environment_risk": "高", "environment": "Production", "count_risk": "低",
        "count_value": 20, "attack_type_risk": "中", "attack_types": ["env_scan"],
        "overall_risk": "高",
    }, ensure_ascii=False, indent=2),
    json.dumps({
        "types": ["env_scan"], "highest_risk": "中",
        "details": [{"type": "env_scan", "label": "环境文件扫描", "risk": "中",
                      "matched": ["/.env.local", "/admin/.env"]}],
    }, ensure_ascii=False, indent=2),
)

SCENES = [
    ("S1-极简",     SCENE1_SYS, SCENE1_USER),
    ("S2-中文+小JSON", SCENE2_SYS, SCENE2_USER),
    ("S3-完整Sys",   SCENE3_SYS, "{\"alert_name\": \"test\"}"),
    ("S4-完整生产",   SCENE4_SYS, SCENE4_USER),
]


@dataclass
class Result:
    model: str
    scene: str
    round: int
    elapsed: float
    content_len: int
    ok: bool
    error: Optional[str] = None


async def call_once(llm: ChatOpenAI, sys_p: str, user_p: str, timeout: int = 120) -> tuple[str, float, Optional[str]]:
    """单次 LLM 调用，返回 (content, elapsed, error)"""
    t0 = time.time()
    try:
        resp = await asyncio.wait_for(
            llm.ainvoke([{"role": "system", "content": sys_p}, {"role": "user", "content": user_p}]),
            timeout=timeout,
        )
        elapsed = time.time() - t0
        content = resp.content if hasattr(resp, "content") else str(resp)
        return (content or "", elapsed, None)
    except asyncio.TimeoutError:
        return ("", time.time() - t0, "TIMEOUT")
    except Exception as e:
        return ("", time.time() - t0, f"{type(e).__name__}: {str(e)[:60]}")


def make_llm(model_id: str) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=model_id,
        temperature=1,
        max_tokens=2048,
        timeout=120,
    )


async def main():
    print("=" * 90)
    print("多模型对比测试 — 3 提供商 × 4 场景 × 3 轮")
    print(f"中转站: {BASE_URL}")
    print("=" * 90)
    print()

    all_results: list[Result] = []

    for model_name, model_id in MODELS.items():
        print(f"{'='*90}")
        print(f"  MODEL: {model_name}")
        print(f"  ID: {model_id}")
        print(f"{'='*90}")

        llm = make_llm(model_id)

        for scene_name, sys_p, user_p in SCENES:
            print(f"\n  --- {scene_name} (sys={len(sys_p)}ch, user={len(user_p)}ch) ---")

            for rnd in range(1, 4):  # 每场景跑 3 轮
                content, elapsed, error = await call_once(llm, sys_p, user_p)
                ok = bool(content and content.strip())
                preview = content[:100].replace("\n", "\\n") if ok else "(EMPTY)"

                result = Result(
                    model=model_name, scene=scene_name, round=rnd,
                    elapsed=elapsed, content_len=len(content), ok=ok, error=error,
                )
                all_results.append(result)

                status = "✅ OK" if ok else ("❌ EMPTY" if not error else f"❌ {error}")
                print(f"    Round {rnd}: {status} | {elapsed:.1f}s | len={len(content)} | {preview}")

                if rnd < 3:
                    await asyncio.sleep(2)  # 轮间短暂间隔

            await asyncio.sleep(3)  # 场景间间隔

        print()

    # ==================== 汇总 ====================
    print("=" * 90)
    print("SUMMARY: 汇总对比表")
    print("=" * 90)
    print()

    # 按模型汇总
    for model_name in MODELS:
        model_results = [r for r in all_results if r.model == model_name]
        ok_count = sum(1 for r in model_results if r.ok)
        total = len(model_results)
        avg_elapsed = sum(r.elapsed for r in model_results if r.ok) / max(ok_count, 1)
        print(f"  {model_name:40s}  {ok_count}/{total} OK  "
              f"({'⭐ 完美' if ok_count==total else '⚠️ 部分失败' if ok_count>0 else '💀 全部失败'})"
              f"  平均 {avg_elapsed:.1f}s")

    print()

    # 按场景汇总
    for scene_name, _, _ in SCENES:
        scene_results = [r for r in all_results if r.scene == scene_name]
        ok_count = sum(1 for r in scene_results if r.ok)
        total = len(scene_results)
        print(f"  {scene_name:40s}  {ok_count}/{total} OK")

    print()

    # 关键结论
    print("=" * 90)
    print("KEY FINDINGS")
    print("=" * 90)

    models_ok = {}
    for model_name in MODELS:
        models_ok[model_name] = sum(1 for r in all_results if r.model == model_name and r.ok)

    all_fail = all(v == 0 for v in models_ok.values())
    all_pass = all(v == 12 for v in models_ok.values())
    some_pass_some_fail = not all_fail and not all_pass

    if all_fail:
        print("  >>> 全部模型都失败 → 问题在中转站 (marketplace.novo-genai.com)")
    elif some_pass_some_fail:
        winners = [k for k, v in models_ok.items() if v > 0]
        losers = [k for k, v in models_ok.items() if v == 0]
        print(f"  >>> 部分通过、部分失败:")
        print(f"      通过: {', '.join(winners)}")
        print(f"      失败: {', '.join(losers)}")
        print(f"  >>> 结论: 问题出在特定提供商，而非中转站")
    else:
        print("  >>> 全部模型通过 → 中转站和所有提供商都正常")


if __name__ == "__main__":
    asyncio.run(main())
