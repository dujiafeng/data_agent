from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.models import PointStruct

from app.conf.app_config import app_config
from app.entities.column_info import ColumnInfo


class ColumnQdrantRepository:
    collection_name: str = "column_info_collection"

    def __init__(self, client: AsyncQdrantClient):
        self.client: AsyncQdrantClient = client

    async def ensure_collection(self):
        if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=app_config.qdrant.embedding_size,
                                                   distance=models.Distance.COSINE)
            )

    async def upsert(self, ids: list[str], embeddings: list[list[float]], payloads: list[dict]):
        point_structs: list[PointStruct] = [PointStruct(id=id, vector=embedding, payload=payload) for
                                            id, embedding, payload in zip(ids, embeddings, payloads)]
        await self.client.upsert(collection_name=self.collection_name, points=point_structs)

    async def search(self, embedding: list[float], score_threshold: float = 0.6, limit: int = 20) -> list[ColumnInfo]:
        # 查询数据
        result = await self.client.query_points(
            collection_name=self.collection_name,
            query=embedding,
            limit=limit,
            score_threshold=score_threshold
        )
        return [ColumnInfo(**point.payload) for point in result.points]

