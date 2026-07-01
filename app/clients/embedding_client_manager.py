import asyncio

from langchain_openai import OpenAIEmbeddings

from app.conf.app_config import EmbeddingConfig, app_config


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig):
        self.client: OpenAIEmbeddings | None = None
        self.config = config

    def _get_url(self):
        return f"http://localhost:8000/v1"

    def init(self):
        self.client = OpenAIEmbeddings(
            base_url=self._get_url(),
            model="Qwen3-Embedding-4B",
            api_key="not-needed")


embedding_client_manager = EmbeddingClientManager(app_config.embedding)

if __name__ == '__main__':
    embedding_client_manager.init()
    client = embedding_client_manager.client


    async def test():
        text = "What is deep learning?"
        query_result = await client.aembed_query(text)
        print(len(query_result))


    asyncio.run(test())
