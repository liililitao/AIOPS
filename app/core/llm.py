"""
LLM 工厂模块
基于 testAIAPI.py 的配置模式: OpenAI-compatible API
使用 langchain_openai.ChatOpenAI，支持模型分层
"""

import asyncio
import hashlib
import logging
from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import get_settings

logger = logging.getLogger("aiops.llm")

# 重试配置
LLM_MAX_RETRIES = 4          # 首次失败后最多重试 4 次（共 5 次尝试）
LLM_RETRY_BASE_DELAY = 2     # 基础等待秒数，每次翻倍: 2, 4, 8, 16


def _hash_user_id(email: str) -> str:
    """对邮箱做 SHA256 哈希，生成 user_id"""
    return hashlib.sha256(email.encode()).hexdigest()


async def call_llm_with_retry(
    llm: ChatOpenAI,
    messages: list[dict],
    max_retries: int | None = None,
    base_delay: int | None = None,
    timeout: int = 120,
):
    """
    带指数退避的 LLM 调用。

    总共 1 次初始尝试 + max_retries 次重试，
    等待间隔: base_delay → base_delay×2 → base_delay×4 → base_delay×8 ...

    Args:
        llm: ChatOpenAI 实例
        messages: 消息列表 [{"role": "...", "content": "..."}]
        max_retries: 最大重试次数，默认使用 LLM_MAX_RETRIES
        base_delay: 基础等待秒数，默认使用 LLM_RETRY_BASE_DELAY
        timeout: 单次调用超时秒数

    Returns:
        (content: str, response: AIMessage)

    Raises:
        ValueError: 空返回
        TimeoutError: 超时
    """
    max_retries = max_retries if max_retries is not None else LLM_MAX_RETRIES
    base_delay = base_delay if base_delay is not None else LLM_RETRY_BASE_DELAY
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            response = await asyncio.wait_for(
                llm.ainvoke(messages),
                timeout=timeout,
            )
            content = response.content if hasattr(response, "content") else str(response)
            if isinstance(content, str) and content.strip():
                if attempt > 0:
                    logger.info(f"[LLM] Succeeded on retry attempt {attempt}")
                return content, response
            else:
                last_error = ValueError("LLM returned empty response")
        except asyncio.TimeoutError:
            last_error = TimeoutError(f"LLM call timed out ({timeout}s)")
        except Exception as e:
            last_error = e

        if attempt < max_retries:
            wait = base_delay * (2 ** attempt)
            logger.warning(
                f"[LLM] Attempt {attempt + 1}/{max_retries + 1} failed "
                f"({type(last_error).__name__}), retrying in {wait}s..."
            )
            await asyncio.sleep(wait)

    raise last_error or ValueError("LLM returned empty after all retries")


def create_llm(
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int | None = None,
    streaming: bool = False,
) -> ChatOpenAI:
    """
    LLM 工厂函数，返回 langchain_openai.ChatOpenAI 实例

    Args:
        model: 模型名称，默认使用 REPORT_MODEL
        temperature: 温度参数
        max_tokens: 最大 token 数
        timeout: 超时时间（秒）
        streaming: 是否流式输出

    Returns:
        ChatOpenAI 实例
    """
    settings = get_settings()

    return ChatOpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        model=model or settings.REPORT_MODEL,
        temperature=temperature if temperature is not None else settings.LLM_TEMPERATURE,
        max_tokens=max_tokens or settings.LLM_MAX_TOKENS,
        timeout=timeout or settings.LLM_TIMEOUT,
        streaming=streaming,
        default_headers={
            "user": _hash_user_id(settings.LLM_USER_EMAIL),
        },
    )


@lru_cache()
def get_router_llm() -> ChatOpenAI:
    """获取 Router 模型（快速/便宜）"""
    return create_llm(model=get_settings().ROUTER_MODEL)


@lru_cache()
def get_planner_llm() -> ChatOpenAI:
    """获取 Planner 模型（中等）"""
    return create_llm(model=get_settings().PLANNER_MODEL)


@lru_cache()
def get_executor_llm() -> ChatOpenAI:
    """获取 Executor 模型（Tool-calling 能力）"""
    return create_llm(model=get_settings().EXECUTOR_MODEL)


@lru_cache()
def get_report_llm() -> ChatOpenAI:
    """获取 Report 模型（最强）"""
    return create_llm(model=get_settings().REPORT_MODEL)


@lru_cache()
def get_rag_chat_llm() -> ChatOpenAI:
    """获取 RAG Chat 模型"""
    return create_llm(
        model=get_settings().RAG_CHAT_MODEL,
        temperature=1,  # gpt-5 only supports temperature=1
        streaming=True,
    )
