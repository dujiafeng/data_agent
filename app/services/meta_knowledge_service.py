import uuid
from dataclasses import asdict
from pathlib import Path

from langchain_huggingface import HuggingFaceEndpointEmbeddings
from omegaconf import OmegaConf

from app.conf.mate_config import MetaConfig
from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.core.log import logger

class MetaKnowledgeService:
    def __init__(self,
                 meta_mysql_repository: MetaMySQLRepository,
                 dw_mysql_repository: DWMySQLRepository,
                 column_qdrant_repository: ColumnQdrantRepository,
                 embedding_client: HuggingFaceEndpointEmbeddings,
                 value_es_repository: ValueESRepository,
                 metric_qdrant_repository: MetricQdrantRepository):
        self.meta_mysql_repository: MetaMySQLRepository = meta_mysql_repository
        self.dw_mysql_repository: DWMySQLRepository = dw_mysql_repository
        self.column_qdrant_repository: ColumnQdrantRepository = column_qdrant_repository
        self.embedding_client: HuggingFaceEndpointEmbeddings = embedding_client
        self.value_es_repository: ValueESRepository = value_es_repository
        self.metric_qdrant_repository: MetricQdrantRepository = metric_qdrant_repository

    async def _save_tables_to_meta_db(self, meta_config: MetaConfig) -> list[ColumnInfo]:
        logger.info("开始同步表信息到 meta 数据库...")
        table_infos: list[TableInfo] = []
        column_infos: list[ColumnInfo] = []

        for table in meta_config.tables:
            logger.info("处理表: {} ({})", table.name, table.role)
            # table -> table_info
            table_info = TableInfo(id=table.name,
                                   name=table.name,
                                   role=table.role,
                                   description=table.description)
            table_infos.append(table_info)

            # 查询字段类型
            column_types = await self.dw_mysql_repository.get_column_types(table.name)
            logger.debug("表 {} 的字段类型: {} 个字段", table.name, len(column_types))

            for column in table.columns:
                # 查询字段取值示例
                column_values = await self.dw_mysql_repository.get_column_values(table.name, column.name)
                logger.debug("字段 {}.{} 取值示例: {} 条", table.name, column.name, len(column_values))
                # column -> column_info
                column_info = ColumnInfo(id=f"{table.name}.{column.name}",
                                         name=column.name,
                                         type=column_types[column.name],
                                         role=column.role,
                                         examples=column_values,
                                         description=column.description,
                                         alias=column.alias,
                                         table_id=table.name)
                column_infos.append(column_info)

        logger.info("待写入: {} 张表, {} 个字段", len(table_infos), len(column_infos))
        async with self.meta_mysql_repository.session.begin():
            self.meta_mysql_repository.save_table_infos(table_infos)
            self.meta_mysql_repository.save_column_infos(column_infos)
        logger.info("表信息写入 meta 数据库完成")

        return column_infos

    async def _save_columns_to_qdrant(self, column_infos: list[ColumnInfo]):
        logger.info("开始为字段信息建立向量索引...")
        await self.column_qdrant_repository.ensure_collection()
        logger.info("Qdrant 集合 '{}' 已就绪", self.column_qdrant_repository.collection_name)

        points: list[dict] = []
        for column_info in column_infos:
            points.append({
                'id': str(uuid.uuid4()),
                'embedding_text': column_info.name,
                'payload': asdict(column_info)
            })

            points.append({
                'id': str(uuid.uuid4()),
                'embedding_text': column_info.description,
                'payload': asdict(column_info)
            })

            for alia in column_info.alias:
                points.append({
                    'id': str(uuid.uuid4()),
                    'embedding_text': alia,
                    'payload': asdict(column_info)
                })

        logger.info("共生成 {} 个文本片段待向量化", len(points))
        # 向量化
        embeddings: list[list[float]] = []
        embedding_texts = [point['embedding_text'] for point in points]
        embedding_batch_size = 20
        total_batches = (len(embedding_texts) + embedding_batch_size - 1) // embedding_batch_size
        for i in range(0, len(embedding_texts), embedding_batch_size):
            batch_embedding_texts = embedding_texts[i:i + embedding_batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(batch_embedding_texts)
            embeddings.extend(batch_embeddings)
            logger.debug("字段向量化进度: {}/{} 批次完成", i // embedding_batch_size + 1, total_batches)

        ids = [point['id'] for point in points]
        payloads = [point['payload'] for point in points]

        await self.column_qdrant_repository.upsert(ids, embeddings, payloads)
        logger.info("字段信息向量索引建立完成，共写入 {} 条向量", len(points))

    async def _save_values_to_es(self, meta_config: MetaConfig):
        logger.info("开始为维度字段取值建立 ES 全文索引...")
        await self.value_es_repository.ensure_index()
        logger.info("ES 索引 '{}' 已就绪", self.value_es_repository.index_name)

        value_infos: list[ValueInfo] = []
        for table in meta_config.tables:
            for column in table.columns:
                if column.sync:
                    logger.debug("同步字段取值: {}.{}", table.name, column.name)
                    current_column_values = await self.dw_mysql_repository.get_column_values(table.name,
                                                                                             column.name, 100000)
                    logger.debug("字段 {}.{} 共 {} 个取值", table.name, column.name, len(current_column_values))
                    current_values_infos = [ValueInfo(id=f"{table.name}.{column.name}.{current_column_value}",
                                                      value=current_column_value,
                                                      column_id=f"{table.name}.{column.name}") for
                                            current_column_value in
                                            current_column_values]
                    value_infos.extend(current_values_infos)

        logger.info("待写入 ES: {} 条文档", len(value_infos))
        await self.value_es_repository.index(value_infos)
        logger.info("字段取值全文索引建立完成")

    async def _save_metrics_to_meta_db(self, meta_config: MetaConfig) -> list[MetricInfo]:
        logger.info("开始同步指标信息到 meta 数据库...")
        metric_infos: list[MetricInfo] = []
        column_metrics: list[ColumnMetric] = []

        for metric in meta_config.metrics:
            logger.info("处理指标: {} - {}", metric.name, metric.description)
            # metric->MetricInfo
            metric_info = MetricInfo(
                id=metric.name,
                name=metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias
            )
            metric_infos.append(metric_info)
            for column in metric.relevant_columns:
                logger.debug("指标 {} 关联字段: {}", metric.name, column)
                # column -> ColumnMetric
                column_metric = ColumnMetric(
                    column_id=column,
                    metric_id=metric.name
                )
                column_metrics.append(column_metric)

        logger.info("待写入: {} 个指标, {} 条关联关系", len(metric_infos), len(column_metrics))
        async with self.meta_mysql_repository.session.begin():
            self.meta_mysql_repository.save_metric_infos(metric_infos)
            self.meta_mysql_repository.save_column_metrics(column_metrics)
        logger.info("指标信息写入 meta 数据库完成")

        return metric_infos

    async def _save_metrics_to_qdrant(self, metric_infos: list[MetricInfo]):
        logger.info("开始为指标信息建立向量索引...")
        await self.metric_qdrant_repository.ensure_collection()
        logger.info("Qdrant 集合 '{}' 已就绪", self.metric_qdrant_repository.collection_name)

        points: list[dict] = []
        for metric_info in metric_infos:
            points.append({
                'id': str(uuid.uuid4()),
                'embedding_text': metric_info.name,
                'payload': asdict(metric_info)
            })

            points.append({
                'id': str(uuid.uuid4()),
                'embedding_text': metric_info.description,
                'payload': asdict(metric_info)
            })

            for alia in metric_info.alias:
                points.append({
                    'id': str(uuid.uuid4()),
                    'embedding_text': alia,
                    'payload': asdict(metric_info)
                })

        logger.info("共生成 {} 个文本片段待向量化", len(points))
        # 向量化
        embeddings: list[list[float]] = []
        embedding_texts = [point['embedding_text'] for point in points]
        embedding_batch_size = 20
        total_batches = (len(embedding_texts) + embedding_batch_size - 1) // embedding_batch_size
        for i in range(0, len(embedding_texts), embedding_batch_size):
            batch_embedding_texts = embedding_texts[i:i + embedding_batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(batch_embedding_texts)
            embeddings.extend(batch_embeddings)
            logger.debug("指标向量化进度: {}/{} 批次完成", i // embedding_batch_size + 1, total_batches)

        ids = [point['id'] for point in points]
        payloads = [point['payload'] for point in points]

        await self.metric_qdrant_repository.upsert(ids, embeddings, payloads)
        logger.info("指标信息向量索引建立完成，共写入 {} 条向量", len(points))

    async def build(self, config_path: Path):
        logger.info("=" * 50)
        logger.info("开始构建元数据知识，配置文件: {}", config_path)
        logger.info("=" * 50)

        # 1. 读取配置文件
        logger.info("步骤1: 读取配置文件")
        context = OmegaConf.load(config_path)
        schema = OmegaConf.structured(MetaConfig)
        meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
        logger.info("配置文件加载完成: {} 张表, {} 个指标",
                     len(meta_config.tables or []), len(meta_config.metrics or []))

        # 2. 根据配置文件同步指定的表信息
        if meta_config.tables:
            logger.info("步骤2: 同步表信息")
            # 2.1 将表信息和字段信息保存meta数据库中
            column_infos = await self._save_tables_to_meta_db(meta_config)

            # 2.2 对字段信息建立向量索引
            await self._save_columns_to_qdrant(column_infos)

            # 2.3 对指定的维度字段取值建立全文索引
            await self._save_values_to_es(meta_config)
        else:
            logger.warning("配置中未定义任何表信息，跳过步骤2")

        # 3. 根据配置文件同步指定的指标信息
        if meta_config.metrics:
            logger.info("步骤3: 同步指标信息")
            # 3.1 将指标信息保存meta数据库中
            metric_infos = await self._save_metrics_to_meta_db(meta_config)

            # 3.2 对指标信息建立向量索引
            await self._save_metrics_to_qdrant(metric_infos)
        else:
            logger.warning("配置中未定义任何指标信息，跳过步骤3")

        logger.info("=" * 50)
        logger.info("元数据知识构建完成")
        logger.info("=" * 50)
