"""
知识库文档管理 API 路由
Upload / List / Delete 已索引的运维文档
"""

import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Header
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.services.document_service import upload_document, list_documents, delete_document, search_documents

logger = logging.getLogger("aiops.api.documents")
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


def _check_admin_token(x_kb_admin_token: str = Header(default="", alias="X-KB-Admin-Token")):
    """验证管理员 Token"""
    settings = get_settings()
    if not settings.KB_ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="知识库写操作已锁定，请先配置 KB_ADMIN_TOKEN")
    if x_kb_admin_token != settings.KB_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="管理员 Token 无效")
    return True


@router.post("/upload")
async def upload(file: UploadFile = File(...), _auth=Header(default=None, alias="X-KB-Admin-Token")):
    """上传文档到知识库"""
    settings = get_settings()
    if not settings.KB_ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="知识库写操作已锁定，请先配置 KB_ADMIN_TOKEN")

    token = _auth if isinstance(_auth, str) else ""
    if token != settings.KB_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="管理员 Token 无效")

    try:
        content = await file.read()
        result = upload_document(file.filename, content)
        return {
            "code": "SUCCESS",
            "message": f"已索引 {result['chunks_indexed']} 个 chunk",
            "data": result,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[DOCS] Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_all():
    """获取知识库文档列表"""
    try:
        docs = list_documents()
        return {
            "code": "SUCCESS",
            "message": "ok",
            "data": {
                "total": len(docs),
                "documents": docs,
            },
        }
    except Exception as e:
        logger.error(f"[DOCS] List failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search(q: str = "", top_k: int = 5):
    """向量语义搜索知识库"""
    if not q.strip():
        return {"code": "SUCCESS", "message": "ok", "data": {"results": [], "query": q}}
    try:
        results = search_documents(q, top_k=top_k)
        return {
            "code": "SUCCESS",
            "message": f"找到 {len(results)} 条结果",
            "data": {"results": results, "query": q},
        }
    except Exception as e:
        logger.error(f"[DOCS] Search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{source:path}")
async def delete(source: str, _auth=Header(default=None, alias="X-KB-Admin-Token")):
    """删除指定文档"""
    settings = get_settings()
    if not settings.KB_ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="知识库写操作已锁定，请先配置 KB_ADMIN_TOKEN")

    token = _auth if isinstance(_auth, str) else ""
    if token != settings.KB_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="管理员 Token 无效")

    try:
        result = delete_document(source)
        return {
            "code": "SUCCESS",
            "message": f"已删除 {result['deleted_chunks']} 个 chunk",
            "data": result,
        }
    except Exception as e:
        logger.error(f"[DOCS] Delete failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
