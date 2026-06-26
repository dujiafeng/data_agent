from typing import Annotated, Any, AsyncGenerator

from fastapi.params import Depends

from app.clients.embedding_client_manager import EmbeddingClientManager, embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.query_service import QueryService
from sqlalchemy.ext.asyncio import AsyncSession


async def get_meta_session() -> AsyncGenerator[Any, Any]:
    async with meta_mysql_client_manager.session_factory() as meta_session:
        yield meta_session


async def get_dw_session() -> AsyncGenerator[Any, Any]:
    async with dw_mysql_client_manager.session_factory() as dw_session:
        yield dw_session


async def get_meta_mysql_repository(
        meta_session: Annotated[AsyncSession, Depends(get_meta_session)]) -> MetaMySQLRepository:
    return MetaMySQLRepository(session=meta_session)


async def get_dw_mysql_repositor(dw_session: Annotated[AsyncSession, Depends(get_dw_session)]) -> DWMySQLRepository:
    return DWMySQLRepository(session=dw_session)


async def get_column_qdrant_repository() -> ColumnQdrantRepository:
    return ColumnQdrantRepository(qdrant_client_manager.client)


async def get_metric_qdrant_repository() -> MetricQdrantRepository:
    return MetricQdrantRepository(qdrant_client_manager.client)


async def get_value_es_repository() -> ValueESRepository:
    return ValueESRepository(es_client_manager.client)


async def get_embedding_client_manager() -> EmbeddingClientManager:
    return embedding_client_manager


async def get_query_service(meta_mysql_repository: Annotated[MetaMySQLRepository, Depends(get_meta_mysql_repository)],
                            dw_mysql_repositor: Annotated[DWMySQLRepository, Depends(get_dw_mysql_repositor)],
                            column_qdrant_repository: Annotated[
                                ColumnQdrantRepository, Depends(get_column_qdrant_repository)],
                            metric_qdrant_repository: Annotated[
                                MetricQdrantRepository, Depends(get_metric_qdrant_repository)],
                            value_es_repository: Annotated[ValueESRepository, Depends(get_value_es_repository)],
                            embedding_client_manager: Annotated[
                                EmbeddingClientManager, Depends(get_embedding_client_manager)]) -> QueryService:
    return QueryService(
        meta_mysql_repository=meta_mysql_repository,
        dw_mysql_repositor=dw_mysql_repositor,
        column_qdrant_repository=column_qdrant_repository,
        metric_qdrant_repository=metric_qdrant_repository,
        value_es_repository=value_es_repository,
        embedding_client_manager=embedding_client_manager
    )
