"""Embedding 服务 — 支持 OpenAI 兼容接口、Ollama 本地模型"""

import logging
from typing import List

import httpx
from app.config import get_settings

logger = logging.getLogger("aiops.embedding")


def embed(texts: List[str]) -> List[List[float]]:
    """
    将文本列表转为向量

    Args:
        texts: 待向量化的文本列表

    Returns:
        向量列表，每个向量为 float 数组
    """
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER

    if provider == "ollama":
        return _embed_ollama(texts, settings)
    else:
        # openai / dashscope / 兼容接口
        return _embed_openai_compatible(texts, settings)


def _embed_openai_compatible(texts: List[str], settings) -> List[List[float]]:
    """OpenAI 兼容接口 (text-embedding-3-small 等)"""
    url = (settings.EMBEDDING_BASE_URL or settings.LLM_BASE_URL).rstrip("/") + "/embeddings"
    api_key = settings.EMBEDDING_API_KEY or settings.LLM_API_KEY

    # 分批 (OpenAI 单次最多约 2048 tokens)
    batch_size = 20
    all_vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = httpx.post(
            url,
            json={"input": batch, "model": settings.EMBEDDING_MODEL},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Embedding API {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        all_vectors.extend([item["embedding"] for item in data["data"]])
    return all_vectors


def _embed_ollama(texts: List[str], settings) -> List[List[float]]:
    """Ollama 本地 embedding (bge-m3 等)"""
    url = (settings.EMBEDDING_BASE_URL or "http://localhost:11434").rstrip("/") + "/api/embed"
    batch_size = getattr(settings, 'OLLAMA_EMBEDDING_BATCH_SIZE', 8)
    all_vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        resp = httpx.post(
            url,
            json={"model": settings.EMBEDDING_MODEL, "input": batch},
            timeout=120,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama embedding {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        all_vectors.extend(data["embeddings"])
    return all_vectors


def embed_query(text: str) -> List[float]:
    """单文本向量化 (用于检索)"""
    return embed([text])[0]
