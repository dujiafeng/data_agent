import asyncio
import os
from typing import Optional

from langchain_community.embeddings import DashScopeEmbeddings

from app.conf.app_config import EmbeddingConfig, app_config

from dotenv import load_dotenv
load_dotenv()

class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.client: Optional[DashScopeEmbeddings] = None
        self.config = config

    def _get_url(self):
        return f"http://{self.config.host}:{self.config.port}"

    def init(self):
        self.client = DashScopeEmbeddings(
            model=self.config.model,
            dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),)


embedding_client_manager = EmbeddingClientManager(app_config.embedding)

if __name__ == '__main__':
    embedding_client_manager.init()
    client = embedding_client_manager.client


    async def test():
        text = "What is deep learning?"
        query_result = await client.aembed_documents([text])
        print(query_result[:3])


    asyncio.run(test())
