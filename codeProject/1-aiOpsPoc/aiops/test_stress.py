"""
Stress test: call API repeatedly to reproduce intermittent empty responses
10 sequential calls, then 10 concurrent calls
"""
import asyncio
import json
import os
import time

from langchain_openai import ChatOpenAI

LLM = ChatOpenAI(
    base_url="https://api.marketplace.novo-genai.com/v1",
    api_key=os.getenv("LLM_API_KEY", ""),
    model="openai_gpt5",
    temperature=1,
    max_tokens=512,
    timeout=60,
)

SYS = """你是一位资深的网络安全运维专家。请根据以下告警数据和 CMDB 资产信息，生成一份专业的 WAF 告警分析报告。

报告要求:
1. 使用 Markdown 格式
2. 包含以下章节:
   - 告警概要
   - 告警数据详情
   - CMDB 资产信息
   - 攻击分析
   - 综合风险评估
3. 标注为【证据溯源】"""

USER = json.dumps({
    "alert_name": "WAF SQL Injection Alert",
    "trigger_time": "2026-07-27 10:00:00",
    "event_count": 150,
}, ensure_ascii=False)


async def call_api(idx: int, label: str) -> dict:
    t0 = time.time()
    try:
        resp = await asyncio.wait_for(
            LLM.ainvoke([
                {"role": "system", "content": SYS},
                {"role": "user", "content": USER},
            ]),
            timeout=45,
        )
        content = resp.content if hasattr(resp, "content") else str(resp)
        elapsed = time.time() - t0
        return {"label": label, "idx": idx, "len": len(content),
                "ok": len(content) > 10, "elapsed": f"{elapsed:.1f}s"}
    except Exception as e:
        elapsed = time.time() - t0
        return {"label": label, "idx": idx, "len": 0, "ok": False,
                "error": str(e)[:80], "elapsed": f"{elapsed:.1f}s"}


def print_table(results):
    print(f"{'#':<5} {'Status':<10} {'Len':<8} {'Time':<8} {'Detail'}")
    print("-" * 65)
    for r in results:
        status = "OK" if r["ok"] else "EMPTY"
        detail = r.get("error", "")
        print(f"{r['label']}-{r['idx']:<2} {status:<10} {r['len']:<8} {r['elapsed']:<8} {detail}")


async def main():
    # ---- Sequential calls ----
    print("=" * 65)
    print("PHASE 1: 10 Sequential Calls (with 1s delay)")
    print("=" * 65)
    seq_results = []
    for i in range(1, 11):
        r = await call_api(i, "SEQ")
        seq_results.append(r)
        status = "OK" if r["ok"] else "EMPTY"
        print(f"  SEQ-{i:02d}  {status:<10} len={r['len']:<6} {r['elapsed']}")
        if i < 10:
            await asyncio.sleep(1)

    seq_ok = sum(1 for r in seq_results if r["ok"])
    print(f"\n  Sequential: {seq_ok}/10 OK, {10-seq_ok}/10 EMPTY\n")

    # ---- Concurrent calls ----
    print("=" * 65)
    print("PHASE 2: 10 Concurrent Calls (simultaneous)")
    print("=" * 65)
    tasks = [call_api(i, "CONC") for i in range(1, 11)]
    conc_results = await asyncio.gather(*tasks)
    print_table(conc_results)

    conc_ok = sum(1 for r in conc_results if r["ok"])
    print(f"\n  Concurrent: {conc_ok}/10 OK, {10-conc_ok}/10 EMPTY\n")

    # ---- Final Summary ----
    print("=" * 65)
    print("FINAL SUMMARY")
    print("=" * 65)
    total_ok = seq_ok + conc_ok
    total_empty = 20 - total_ok
    print(f"  Total: {total_ok}/20 OK, {total_empty}/20 EMPTY")

    if total_empty == 0:
        print("  >>> API is fully stable right now")
    elif total_empty < 5:
        print(f"  >>> API has occasional failures ({total_empty}/20)")
    elif total_empty < 15:
        print(f"  >>> API is moderately unstable ({total_empty}/20)")
    else:
        print(f"  >>> API is severely degraded ({total_empty}/20)")


if __name__ == "__main__":
    asyncio.run(main())
