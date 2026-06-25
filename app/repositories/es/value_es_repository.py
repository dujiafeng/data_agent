from dataclasses import asdict

from elasticsearch import AsyncElasticsearch

from app.core.log import logger
from app.entities.value_info import ValueInfo


class ValueESRepository:
    index_name = "value_index"
    index_mappings = {
        "dynamic": False,
        "properties": {
            "id": {"type": "keyword"},
            "value": {"type": "text", "analyzer": "ik_max_word", "search_analyzer": "ik_max_word"},
            "column_id": {"type": "keyword"}
        }
    }

    def __init__(self, client: AsyncElasticsearch):
        self.client = client

    async def ensure_index(self):
        if not await self.client.indices.exists(index=self.index_name):
            logger.info("创建 ES 索引 '{}'", self.index_name)
            await self.client.indices.create(
                index=self.index_name,
                mappings=self.index_mappings
            )
        else:
            logger.debug("ES 索引 '{}' 已存在", self.index_name)

    async def index(self, value_infos: list[ValueInfo], batch_size=20):
        logger.info("开始写入 {} 条文档到 ES 索引 '{}'", len(value_infos), self.index_name)
        for i in range(0, len(value_infos), batch_size):
            batch_value_infos = value_infos[i:i + batch_size]
            batch_operations = []
            for value_info in batch_value_infos:
                batch_operations.append(
                    {
                        "index": {
                            "_index": self.index_name
                        }
                    }
                )
                batch_operations.append(asdict(value_info))
            await self.client.bulk(operations=batch_operations)
            logger.debug("批次写入 {} 条文档完成", len(batch_value_infos))

    async def search(self, keyword: str, score_threshold: float = 0.6, limit: int = 20) -> list[ValueInfo]:
        resp = await self.client.search(
            index=self.index_name,
            query={
                "match": {
                    "value": keyword
                }
            },
            size=limit,
            min_score=score_threshold
        )
        return [ValueInfo(**hit['_source']) for hit in resp['hits']['hits']]

