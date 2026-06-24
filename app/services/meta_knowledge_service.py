import uuid
from dataclasses import asdict
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from omegaconf import OmegaConf

from app.core.log import logger
from app.conf.mate_config import MetaConfig
from app.entities.column_info import ColumnInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository


class MetaKnowledgeService:
    def __init__(self, meta_mysql_repository: MetaMySQLRepository, dw_mysql_repository: DWMySQLRepository,
                 column_qdrant_repository: ColumnQdrantRepository, embedding_client: OpenAIEmbeddings,
                 value_es_repository: ValueESRepository):
        self.meta_mysql_repository: MetaMySQLRepository = meta_mysql_repository
        self.dw_mysql_repository: DWMySQLRepository = dw_mysql_repository
        self.column_qdrant_repository: ColumnQdrantRepository = column_qdrant_repository
        self.embedding_client: OpenAIEmbeddings = embedding_client
        self.value_es_repository: ValueESRepository = value_es_repository

    async def build(self, config_path: Path):
        # 1.读取配置文件
        logger.info("加载元数据配置文件: {}", config_path)
        context = OmegaConf.load(config_path)
        schema = OmegaConf.structured(MetaConfig)
        meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
        logger.info("配置加载完成，共 {} 张表, {} 个指标", len(meta_config.tables or []), len(meta_config.metrics or []))

        # 2. 根据配置文件同步指定的表信息和指标信息
        if meta_config.tables:
            table_infos: list[TableInfo] = []
            column_infos: list[ColumnInfo] = []
            # 2.1 将表信息和字段信息保存到数据库中
            for table in meta_config.tables:
                table_info = TableInfo(id=table.name,
                                       name=table.name,
                                       role=table.role,
                                       description=table.description, )
                table_infos.append(table_info)
                column_types = await self.dw_mysql_repository.get_column_types(table.name)
                for column in table.columns:
                    column_values = await self.dw_mysql_repository.get_column_values(table.name, column.name)
                    column_info = ColumnInfo(id=f"{table.name}.{column.name}",
                                             name=column.name,
                                             type=column_types[column.name],
                                             role=column.role,
                                             examples=column_values,
                                             description=column.description,
                                             alias=column.alias,
                                             table_id=table.name, )
                    column_infos.append(column_info)

            async with self.meta_mysql_repository.session.begin():
                self.meta_mysql_repository.save_table_infos(table_infos)
                self.meta_mysql_repository.save_column_infos(column_infos)
                logger.info("表信息已持久化: {} 张表, {} 个字段", len(table_infos), len(column_infos))

            # 2.2 对字段信息简历向量索引
            await self.column_qdrant_repository.ensure_collection()

            points: list[dict] = []
            for column_info in column_infos:
                points.append({
                    'id': uuid.uuid4(),
                    'embedding_text': column_info.name,
                    'payload': asdict(column_info),
                })

                points.append({
                    'id': uuid.uuid4(),
                    'embedding_text': column_info.description,
                    'payload': asdict(column_info),
                })

                for alia in column_info.alias:
                    points.append({
                        'id': uuid.uuid4(),
                        'embedding_text': alia,
                        'payload': asdict(column_info),
                    })
            # 向量化
            logger.info("开始向量化 {} 个文本片段", len(points))
            embeddings: list[list[float]] = []
            embedding_texts = [point['embedding_text'] for point in points]
            embedding_batch_size = 20
            for i in range(0, len(embedding_texts), embedding_batch_size):
                embedding_texts_batch = embedding_texts[i:i + embedding_batch_size]
                embedding_results = await self.embedding_client.aembed_documents(embedding_texts_batch)
                embeddings.extend(embedding_results)
                logger.debug("向量化批次 {}/{} 完成", i // embedding_batch_size + 1, (len(embedding_texts) - 1) // embedding_batch_size + 1)

            ids = [point['id'] for point in points]
            payloads = [point['payload'] for point in points]

            await self.column_qdrant_repository.upsert(ids, embeddings, payloads)
            logger.info("字段向量已写入 Qdrant 集合 '{}'", self.column_qdrant_repository.collection_name)
            # 2.3 对指定的维度字段取值建立全文索引
            await self.value_es_repository.ensure_index()
            value_infos: list[ValueInfo] = []
            for table in meta_config.tables:
                for column in table.columns:
                    if not column.sync:
                        break
                    # 查询字段取值
                    current_column_values = await self.dw_mysql_repository.get_column_values(table.name, column.name,
                                                                                             100000)
                    current_column_infos = [ValueInfo(id=f'{table.name}.{column.name}.{current_column_value}', value=current_column_value,
                               column_id=f'{table.name}.{column.name}') for current_column_value in
                     current_column_values]

                    value_infos.extend(current_column_infos)

            logger.info("开始写入 {} 个字段取值到 ES", len(value_infos))
            await self.value_es_repository.index(value_infos)

        # 3 根据配置文件同步指定的指标信息
        if meta_config.metrics:
            pass
            # 3.1 将指标信息保存到meta数据库中
            # 3.2 对指标信息建立向量索引
