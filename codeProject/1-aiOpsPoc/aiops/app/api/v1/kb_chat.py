"""AIOps 知识库问答 API — 基于 Milvus 向量检索 + LLM RAG 回答"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.services.document_service import search_documents

logger = logging.getLogger("aiops.api.kb_chat")
router = APIRouter(prefix="/api/v1/kb-chat", tags=["kb-chat"])


class KBChatRequest(BaseModel):
    question: str


KB_SYSTEM_PROMPT = """你是一个 AIOps 智能运维知识库助手。你会收到从运维知识库中检索到的相关文档片段，
请基于这些上下文回答用户的问题。

规则：
1. 优先基于提供的知识库内容回答，如果知识库没有相关信息，如实告知
2. 回答要专业、准确、简洁，适合运维人员阅读
3. 如果涉及生产环境操作，提醒用户注意变更流程
4. 可以引用知识库中的具体步骤或命令
5. 如果知识库内容不足以回答问题，可以结合你的运维知识给出建议，但要标明哪些是知识库内容、哪些是通用建议"""


def _build_kb_context(search_results: list[dict]) -> str:
    """将 Milvus 搜索结果拼接为 LLM 上下文"""
    if not search_results:
        return "（知识库中未找到相关内容）"

    parts = ["## 知识库检索结果\n"]
    for i, r in enumerate(search_results, 1):
        source = r.get("source", "未知")
        score = r.get("score", 0)
        text = r.get("text", "")
        parts.append(f"### 文档 {i}: {source} (相关度: {score:.2f})")
        parts.append(text[:2000])  # 每段最多 2000 字符
        parts.append("")
    return "\n".join(parts)


@router.post("")
async def kb_chat(request: KBChatRequest):
    """知识库 RAG 问答 — 搜索向量库 + LLM 生成回答"""
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")

    # 1. 向量搜索知识库
    try:
        search_results = search_documents(question, top_k=5)
        logger.info(f"[KB-CHAT] 检索到 {len(search_results)} 条结果")
    except Exception as e:
        logger.warning(f"[KB-CHAT] 检索失败: {e}")
        search_results = []

    # 2. 构建 RAG 上下文
    context = _build_kb_context(search_results)
    user_msg = f"{context}\n\n用户提问: {question}"

    # 3. 调用 LLM (带重试)
    try:
        from app.core.llm import get_rag_chat_llm, call_llm_with_retry
        llm = get_rag_chat_llm()
        answer, _ = await call_llm_with_retry(llm, [
            {"role": "system", "content": KB_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ])
        return {
            "answer": answer,
            "sources": [
                {"source": r.get("source", ""), "score": r.get("score", 0)}
                for r in search_results
            ],
        }
    except TimeoutError:
        logger.error("[KB-CHAT] LLM timeout after all retries")
        raise HTTPException(status_code=504, detail="AI 服务响应超时")
    except ValueError as e:
        logger.error(f"[KB-CHAT] LLM returned empty: {e}")
        raise HTTPException(status_code=500, detail="AI 服务返回空响应，请稍后重试")
    except Exception as e:
        logger.error(f"[KB-CHAT] LLM failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI 服务暂时不可用: {str(e)}")
