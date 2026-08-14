"""
文档服务 - 知识库文档的存储和检索

双存储模式:
  - 文件系统 (始终启用): 存储原始文件 + JSON 索引
  - Milvus 向量库 (MILVUS_ENABLED=true): 向量化 + 语义检索
"""

import json
import hashlib
import logging
from datetime import datetime
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger("aiops.documents")

ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml"}
CHUNK_INDEX_FILE = "chunk_index.json"


def _kb_dir() -> Path:
    """知识库存储目录"""
    settings = get_settings()
    kb_dir = settings.project_root / "data" / "kb_docs"
    kb_dir.mkdir(parents=True, exist_ok=True)
    return kb_dir


def _load_index() -> dict:
    """加载分块索引"""
    idx_path = _kb_dir() / CHUNK_INDEX_FILE
    if idx_path.exists():
        return json.loads(idx_path.read_text(encoding="utf-8"))
    return {"documents": {}}


def _save_index(index: dict):
    """保存分块索引"""
    idx_path = _kb_dir() / CHUNK_INDEX_FILE
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def _simple_chunk(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """简易分块：按段落 + 大小切分"""
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(current) + len(p) < chunk_size:
            current = (current + "\n\n" + p).strip()
        else:
            if current:
                chunks.append(current)
            current = p
            # 处理超长段落
            while len(current) > chunk_size:
                chunks.append(current[:chunk_size])
                current = current[chunk_size - overlap:]
    if current:
        chunks.append(current)
    return chunks if chunks else [text[:chunk_size]]


def upload_document(filename: str, content: bytes) -> dict:
    """
    上传并索引文档

    Args:
        filename: 原始文件名
        content: 文件内容 (bytes)

    Returns:
        {"source": str, "chunks_indexed": int, "bytes": int}

    Raises:
        ValueError: 文件类型不支持或内容无效
    """
    # 验证扩展名
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {ext}，支持: {', '.join(ALLOWED_EXTENSIONS)}")

    # 解码内容
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("文件编码不支持，请使用 UTF-8")

    if not text.strip():
        raise ValueError("文件内容为空")

    # 保存原始文件
    safe_name = _safe_filename(filename)
    doc_path = _kb_dir() / safe_name
    doc_path.write_bytes(content)

    # 分块
    chunks = _simple_chunk(text)
    chunk_hashes = [hashlib.md5(c.encode()).hexdigest()[:12] for c in chunks]

    # 更新索引
    index = _load_index()
    index["documents"][safe_name] = {
        "original_name": filename,
        "uploaded_at": datetime.now().isoformat(),
        "bytes": len(content),
        "chunks": len(chunks),
        "chunk_hashes": chunk_hashes,
    }
    _save_index(index)

    # ---- Milvus 向量化 (如果启用) ----
    settings = get_settings()
    if settings.MILVUS_ENABLED:
        try:
            from app.core.milvus import connect, ensure_collection, insert_chunks
            from app.core.embedding import embed

            connect()
            collection = settings.MILVUS_COLLECTION
            ensure_collection(collection, dim=_get_embedding_dim())

            # 向量化 + 写入
            vectors = embed(chunks)
            rows = []
            for j, (chunk_text, vec) in enumerate(zip(chunks, vectors)):
                rows.append({
                    "vector": vec,
                    "text": chunk_text,
                    "source": filename,
                    "chunk_index": j,
                })
            inserted = insert_chunks(rows, collection)
            logger.info(f"[DOCS] Milvus indexed {inserted}/{len(chunks)} chunks for '{filename}'")
        except Exception as e:
            logger.warning(f"[DOCS] Milvus indexing skipped: {e} (file index still saved)")

    logger.info(f"[DOCS] Indexed {safe_name}: {len(chunks)} chunks, {len(content)} bytes")
    return {
        "source": filename,
        "chunks_indexed": len(chunks),
        "bytes": len(content),
    }


def list_documents() -> list[dict]:
    """列出所有已索引文档"""
    index = _load_index()
    docs = []
    for safe_name, info in index.get("documents", {}).items():
        docs.append({
            "source": info.get("original_name", safe_name),
            "chunk_count": info.get("chunks", 0),
            "bytes": info.get("bytes", 0),
            "uploaded_at": info.get("uploaded_at", ""),
        })
    docs.sort(key=lambda d: d.get("uploaded_at", ""), reverse=True)
    return docs


def delete_document(source: str) -> dict:
    """
    删除指定文档

    Args:
        source: 原始文件名

    Returns:
        {"source": str, "deleted_chunks": int}
    """
    index = _load_index()
    docs = index.get("documents", {})

    # 按 original_name 反查 safe_name
    target_key = None
    for key, info in docs.items():
        if info.get("original_name") == source:
            target_key = key
            break

    if not target_key:
        # 也尝试直接匹配 key
        safe_name = _safe_filename(source)
        if safe_name in docs:
            target_key = safe_name

    if not target_key:
        logger.warning(f"[DOCS] Document not found in index: {source}")
        return {"source": source, "deleted_chunks": 0}

    # 删除文件
    doc_path = _kb_dir() / target_key
    if doc_path.exists():
        doc_path.unlink()

    # 删除索引
    deleted = docs[target_key].get("chunks", 0)
    del docs[target_key]
    _save_index(index)

    # 删除 Milvus 向量 (如果启用)
    settings = get_settings()
    if settings.MILVUS_ENABLED:
        try:
            from app.core.milvus import delete_by_source
            deleted_vec = delete_by_source(source)
            logger.info(f"[DOCS] Milvus deleted {deleted_vec} vectors for '{source}'")
        except Exception as e:
            logger.warning(f"[DOCS] Milvus delete skipped: {e}")

    logger.info(f"[DOCS] Deleted {target_key}: {deleted} chunks")
    return {"source": source, "deleted_chunks": deleted}


def search_documents(
    query: str, top_k: int = 5, raise_on_error: bool = False
) -> list[dict]:
    """向量语义搜索知识库"""
    settings = get_settings()
    if not settings.MILVUS_ENABLED:
        return []

    try:
        from app.core.milvus import connect, search
        from app.core.embedding import embed_query

        connect()
        query_vec = embed_query(query)
        results = search(query_vec, top_k=top_k, raise_on_error=raise_on_error)

        hits = []
        for r in results:
            entity = r.get("entity", {}) if isinstance(r, dict) else {}
            hits.append({
                "score": r.get("distance", 0) if isinstance(r, dict) else 0,
                "text": entity.get("text", ""),
                "source": entity.get("source", ""),
                "chunk_index": entity.get("chunk_index", 0),
            })
        return hits
    except Exception as e:
        logger.warning(f"[DOCS] Search failed: {e}")
        if raise_on_error:
            raise
        return []


def _get_embedding_dim() -> int:
    """获取当前 embedding 模型的向量维度"""
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER
    model = settings.EMBEDDING_MODEL

    if provider == "ollama":
        return 1024  # bge-m3
    if "3-small" in model:
        return 1536
    if "3-large" in model:
        return 3072
    if "ada" in model:
        return 1536
    return 1024  # 默认


def _safe_filename(filename: str) -> str:
    """生成安全的存储文件名"""
    name = Path(filename).stem
    ext = Path(filename).suffix
    # 替换特殊字符
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
    if not safe:
        safe = "doc"
    # 加时间戳防冲突
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{safe}_{ts}{ext}"
