"""Milvus 向量数据库客户端 — 支持 milvus-lite (免 Docker) 和远程 Milvus"""

import logging
from typing import List, Optional

from app.config import get_settings

logger = logging.getLogger("aiops.milvus")

_milvus_server = None
_client = None


def _start_milvus_lite(data_dir: str = "./milvus_data") -> str:
    """启动嵌入式 milvus-lite，返回 URI。已运行则复用。"""
    global _milvus_server
    from milvus_lite import server_manager_instance
    # 检查是否已有运行实例
    if _milvus_server is not None:
        try:
            from pymilvus import MilvusClient
            MilvusClient(uri=_milvus_server, timeout=2).list_collections()
            return _milvus_server
        except Exception:
            _milvus_server = None
    uri = server_manager_instance.start_and_get_uri(data_dir)
    _milvus_server = uri
    logger.info(f"Milvus Lite started: {uri}")
    return uri


def connect() -> bool:
    """连接 Milvus — 优先 milvus-lite (免 Docker)，失败则试远程"""
    global _client
    settings = get_settings()
    if not settings.MILVUS_ENABLED:
        return False

    # 优先 milvus-lite (本地无需 Docker)
    try:
        from pymilvus import MilvusClient
        uri = _start_milvus_lite("./milvus_data")
        _client = MilvusClient(uri=uri, timeout=10)
        _client.list_collections()
        logger.info(f"Milvus Lite 已就绪: {uri}")
        return True
    except Exception as e:
        logger.debug(f"Milvus Lite 不可用: {e}")

    # 回退: 远程 Milvus
    try:
        from pymilvus import MilvusClient
        client = MilvusClient(
            uri=f"http://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}",
            timeout=5,
        )
        client.list_collections()
        _client = client
        logger.info(f"Milvus 已连接: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        return True
    except Exception as e2:
        logger.warning(f"Milvus 不可用: {e2}")
        return False


def get_client():
    """获取 MilvusClient 实例"""
    if _client is None:
        connect()
    return _client


def ensure_collection(name: str, dim: int = 1024) -> bool:
    """确保 collection 存在，不存在则创建"""
    client = get_client()
    if client is None:
        return False

    if client.has_collection(name):
        logger.info(f"Collection '{name}' 已存在")
        return True

    from pymilvus import DataType

    schema = client.create_schema(enable_dynamic_field=True)
    schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=dim)
    schema.add_field("text", DataType.VARCHAR, max_length=65535)
    schema.add_field("source", DataType.VARCHAR, max_length=512)
    schema.add_field("chunk_index", DataType.INT64)

    client.create_collection(name, schema=schema)
    # 创建 IVF_FLAT 索引 (milvus-lite 兼容)
    index_params = client.prepare_index_params()
    index_params.add_index("vector", index_type="IVF_FLAT", metric_type="COSINE", params={"nlist": 128})
    client.create_index(name, index_params=index_params)
    client.load_collection(name)
    logger.info(f"Collection '{name}' 已创建 (dim={dim})")
    return True


def insert_chunks(chunks: list[dict], collection: str = None) -> int:
    """批量插入向量块，返回插入数"""
    client = get_client()
    if client is None:
        return 0
    col = collection or get_settings().MILVUS_COLLECTION
    if not chunks:
        return 0
    client.load_collection(col)  # 确保已加载
    result = client.insert(col, chunks)
    return result.get("insert_count", 0)


def search(
    query_vector: list[float],
    top_k: int = 5,
    collection: str = None,
    raise_on_error: bool = False,
) -> list[dict]:
    """向量相似度搜索"""
    client = get_client()
    if client is None:
        return []
    col = collection or get_settings().MILVUS_COLLECTION
    try:
        client.load_collection(col)  # 确保已加载
        results = client.search(
            col, data=[query_vector], limit=top_k,
            output_fields=["text", "source", "chunk_index"],
        )
        return results[0] if results else []
    except Exception as e:
        logger.warning(f"搜索失败: {e}")
        if raise_on_error:
            raise
        return []


def delete_by_source(source: str, collection: str = None) -> int:
    """按 source 删除文档块"""
    client = get_client()
    if client is None:
        return 0
    col = collection or get_settings().MILVUS_COLLECTION
    try:
        result = client.delete(col, filter=f'source == "{source}"')
        return result.get("delete_count", 0)
    except Exception as e:
        logger.warning(f"删除失败: {e}")
        return 0


def disconnect():
    """断开 Milvus 连接"""
    global _client
    if _client:
        try:
            _client.close()
        except Exception:
            pass
        _client = None
