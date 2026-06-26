import json

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.clients.embedding_client_manager import EmbeddingClientManager
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class QueryService:
    def __init__(self,
                 meta_mysql_repository: MetaMySQLRepository,
                 dw_mysql_repositor: DWMySQLRepository,
                 column_qdrant_repository: ColumnQdrantRepository,
                 metric_qdrant_repository: MetricQdrantRepository,
                 value_es_repository: ValueESRepository,
                 embedding_client_manager: EmbeddingClientManager):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repositor

        self.column_qdrant_repository = column_qdrant_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.value_es_repository = value_es_repository

        self.embedding_client_manager = embedding_client_manager

    async def query(self, query):
        state = DataAgentState(query=query)
        context = DataAgentContext(column_qdrant_repository=self.column_qdrant_repository,
                                   metric_qdrant_repository=self.metric_qdrant_repository,
                                   embedding_client=self.embedding_client_manager.client,
                                   value_es_repository=self.value_es_repository,
                                   meta_mysql_repository=self.meta_mysql_repository,
                                   dw_mysql_repository=self.dw_mysql_repository)
        try:
            async for chunk in graph.astream(input=state, context=context, stream_mode="custom"):
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)} \n\n"
        except Exception as e:
            error_result = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_result, ensure_ascii=False, default=str)}  \n\n"
