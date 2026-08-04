"""
Time-graduated test: test LLM API with progressively longer timeouts
to see if the API eventually returns real content at some threshold.
"""
import asyncio
import os
import time

from langchain_openai import ChatOpenAI


def make_llm(timeout: int) -> ChatOpenAI:
    return ChatOpenAI(
        base_url="https://api.marketplace.novo-genai.com/v1",
        api_key=os.getenv("LLM_API_KEY", ""),
        model="openai_gpt5",
        temperature=1,
        max_tokens=2048,
        timeout=timeout,
    )

SYS = """你是一个运维助手。请根据告警数据生成简短分析。"""

USER = """告警名称: WAF SQL Injection
触发时间: 2026-07-27 10:00
事件数量: 150
域名: test.example.com
动作: Blocked"""


async def test_one(label: str, timeout: int, total_wait: int):
    """Single test with given timeout and wait time"""
    t0 = time.time()
    try:
        llm = make_llm(timeout)
        resp = await asyncio.wait_for(
            llm.ainvoke([
                {"role": "system", "content": SYS},
                {"role": "user", "content": USER},
            ]),
            timeout=total_wait,
        )
        elapsed = time.time() - t0
        content = resp.content if hasattr(resp, "content") else str(resp)
        ok = bool(content and content.strip())
        preview = content[:150].replace("\n", "\\n") if ok else "(EMPTY)"
        print(f"  [{label}] timeout={timeout}s wait={total_wait}s → "
              f"elapsed={elapsed:.1f}s len={len(content)} {'OK' if ok else 'EMPTY'} "
              f"| {preview}")
        return ok, elapsed, len(content)
    except asyncio.TimeoutError:
        elapsed = time.time() - t0
        print(f"  [{label}] timeout={timeout}s wait={total_wait}s → "
              f"elapsed={elapsed:.1f}s TIMEOUT")
        return False, elapsed, 0
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  [{label}] timeout={timeout}s wait={total_wait}s → "
              f"elapsed={elapsed:.1f}s ERROR: {type(e).__name__}: {str(e)[:80]}")
        return False, elapsed, 0


async def main():
    print("=" * 75)
    print("TEST: Varying timeouts to check if API is just slow")
    print("=" * 75)
    print()

    # Phase 1: Fixed short prompt, varying client-side wait
    print("--- Phase 1: Short prompt, varying timeout ---")
    tests = [
        ("T60",  60,  60),
        ("T120", 120, 120),
        ("T180", 180, 180),
        ("T300", 300, 300),
        ("T600", 600, 600),
    ]
    for label, timeout, wait in tests:
        await test_one(label, timeout, wait)
        await asyncio.sleep(2)

    print()

    # Phase 2: Same timeout, but call with extremely simple prompt
    print("--- Phase 2: Minimal prompt (Say OK) ---")
    t0 = time.time()
    try:
        llm = make_llm(300)
        resp = await asyncio.wait_for(
            llm.ainvoke([
                {"role": "user", "content": "Say OK"},
            ]),
            timeout=300,
        )
        elapsed = time.time() - t0
        content = resp.content if hasattr(resp, "content") else str(resp)
        print(f"  [SayOK-300s] elapsed={elapsed:.1f}s len={len(content)} "
              f"content={repr(content[:100])}")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  [SayOK-300s] elapsed={elapsed:.1f}s ERROR: {type(e).__name__}")

    print()

    # Phase 3: Streaming mode test
    print("--- Phase 3: Streaming mode (may reveal chunked delivery) ---")
    t0 = time.time()
    try:
        llm = ChatOpenAI(
            base_url="https://api.marketplace.novo-genai.com/v1",
            api_key=os.getenv("LLM_API_KEY", ""),
            model="openai_gpt5",
            temperature=1,
            max_tokens=2048,
            timeout=300,
            streaming=True,
        )
        # With streaming, ainvoke still collects all chunks
        resp = await asyncio.wait_for(
            llm.ainvoke([
                {"role": "system", "content": SYS},
                {"role": "user", "content": USER},
            ]),
            timeout=300,
        )
        elapsed = time.time() - t0
        content = resp.content if hasattr(resp, "content") else str(resp)
        print(f"  [Stream-300s] elapsed={elapsed:.1f}s len={len(content)} "
              f"content={repr(content[:200])}")
    except asyncio.TimeoutError:
        elapsed = time.time() - t0
        print(f"  [Stream-300s] elapsed={elapsed:.1f}s TIMEOUT")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  [Stream-300s] elapsed={elapsed:.1f}s ERROR: {type(e).__name__}: {str(e)[:100]}")

    print()
    print("=" * 75)
    print("DONE")


if __name__ == "__main__":
    asyncio.run(main())
