"""
Test: verify if LLM API gateway filters system prompt content
"""
import asyncio
import os
import sys

from langchain_openai import ChatOpenAI

LLM = ChatOpenAI(
    base_url="https://api.marketplace.novo-genai.com/v1",
    api_key=os.getenv("LLM_API_KEY", ""),
    model="openai_gpt5",
    temperature=1,
    max_tokens=2048,
    timeout=60,
)

# Original prompt (contains sensitive keywords)
SYS_ORIGINAL = """你是一位资深的网络安全运维专家。请根据以下告警数据和 CMDB 资产信息，生成一份专业的 WAF 告警分析报告。

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

# Sanitized prompt (sensitive terms replaced)
SYS_SAFE = """你是一位资深的运维数据分析助手。请根据以下告警数据和 CMDB 资产信息，生成一份专业的 WAF 告警分析报告。

报告要求:
1. 使用 Markdown 格式
2. 包含以下章节:
   - 告警概要 (告警名称、触发时间、风险等级)
   - 告警数据详情 (受影响资源、请求路径、WAF动作)
   - CMDB 资产信息 (证据溯源，附 CMDB 查询方式和结果)
   - 请求特征分析 (请求类型分类、特征分析、风险评估)
   - 综合风险评估 (三维度判定详情)
   - 相关运维参考
3. 对于 CMDB 查询结果和分类结果，必须在报告中标注为[证据溯源]
4. 语言专业、客观、准确
5. 在 Splunk 中查看的原始链接必须保留"""


async def test(label: str, sys_prompt: str) -> str | None:
    try:
        resp = await asyncio.wait_for(
            LLM.ainvoke([
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": "Say OK"},
            ]),
            timeout=30,
        )
        content = resp.content if hasattr(resp, "content") else str(resp)
        preview = content[:200].replace("\n", "\\n")
        print(f"[{label}] len={len(content)} content={preview}")
        return content
    except Exception as e:
        print(f"[{label}] ERROR: {type(e).__name__}: {e}")
        return None


async def main():
    print("=" * 60)
    print("Test 1: ORIGINAL prompt (with sensitive words)")
    print("=" * 60)
    r1 = await test("ORIGINAL", SYS_ORIGINAL)

    print()
    print("=" * 60)
    print("Test 2: SAFE prompt (sensitive words removed)")
    print("=" * 60)
    r2 = await test("SAFE", SYS_SAFE)

    print()
    print("=" * 60)
    print("Test 3: ORIGINAL retry (rule out timing)")
    print("=" * 60)
    r3 = await test("ORIGINAL-RETRY", SYS_ORIGINAL)

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  ORIGINAL 1st: {'PASS' if r1 else 'EMPTY/ERROR'}")
    print(f"  SAFE:          {'PASS' if r2 else 'EMPTY/ERROR'}")
    print(f"  ORIGINAL 2nd: {'PASS' if r3 else 'EMPTY/ERROR'}")

    if r2 and not r1 and not r3:
        print("\n>>> CONCLUSION: Content filter confirmed!")
        print("    The API gateway is filtering system prompts")
        print("    containing security-related keywords.")
    elif r1 and r2:
        print("\n>>> Content filter NOT confirmed - both pass.")
    elif not r1 and not r2:
        print("\n>>> Both fail - likely rate limit or API down.")


if __name__ == "__main__":
    asyncio.run(main())
