from qdrant_client import AsyncQdrantClient, models

from app.conf.app_config import app_config


class ColumnQdrantRepository:

    collection_name: str = "column_info_collection"

    def __init__(self, client: AsyncQdrantClient):
        self.client: AsyncQdrantClient = client

    async def ensure_collection(self):
        if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(size=app_config.qdrant.embedding_size, distance=models.Distance.COSINE)
            )
