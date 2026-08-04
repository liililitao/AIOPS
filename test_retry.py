"""
Test the retry logic in call_llm_with_retry
"""
import asyncio
import time

from app.core.llm import get_report_llm, call_llm_with_retry

SYS = """你是一位资深的网络安全运维专家。请根据以下告警数据生成一份分析报告。"""

USER = """{"alert_name": "WAF SQL Injection", "event_count": 150}"""


async def main():
    llm = get_report_llm()
    print(f"LLM config: base_url={llm.openai_api_base}, model={llm.model_name}")
    print(f"max_tokens={llm.max_tokens}, temperature={llm.temperature}")
    print()

    t0 = time.time()

    try:
        content, response = await call_llm_with_retry(llm, [
            {"role": "system", "content": SYS},
            {"role": "user", "content": USER},
        ])
        elapsed = time.time() - t0
        print(f"SUCCESS in {elapsed:.1f}s")
        print(f"Content length: {len(content)}")
        print(f"Preview: {content[:300]}")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"FAILED after {elapsed:.1f}s: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
