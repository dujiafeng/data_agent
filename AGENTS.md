# data-agent

## 项目结构

```
app/
  agent/          # LangGraph agent (graph.py 定义拓扑)
    nodes/        # 每个 .py 文件一个节点, 签名: async fn(state, runtime)
  clients/        # 外部服务连接管理 (单例, init/close)
  conf/           # OmegaConf 配置加载 + dataclass schema
  core/log.py     # loguru 日志配置, import: from app.core.log import logger
  entities/       # dataclass 业务实体
  models/         # SQLAlchemy ORM 模型 (Base = DeclarativeBase)
  repositories/   # 数据访问层 (mysql/meta, mysql/dw, qdrant, es)
  scripts/        # 可执行脚本 (如 build_meta_knowledge)
  services/       # 业务逻辑
prompts/          # LLM prompt 模板, 通过 app/prompt/prompt_loader.py 加载
conf/
  app_config.yaml # ⚠️ 含明文密码/API key, 不提交
  meta_config.yaml # 元数据知识构建配置
```

## 关键命令

```bash
uv run python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml
uv run python -m app.agent.graph          # 测试 agent
uv run python -m app.agent.llm             # 测试 LLM 连接
uv run python main.py                      # 数据库连接检测
uv add <package>                           # 添加依赖
```

## 重要约定

- **`conf/app_config.yaml` 不提交**（含密码和 API key）
- **事务**: `async_sessionmaker(autobegin=False)`, 统一用 `async with session.begin():` 管理
- **日志**: 使用 `from app.core.log import logger` (loguru), 不要用 print 或 logging
- **Agent 节点签名**: `async def node_name(state: DataAgentState, runtime: Runtime[DataAgentContext])`
- **Embeding**: 通过 DashScope, API key 从 `DASHSCOPE_API_KEY` 环境变量读取 (dotenv)
- **包管理**: uv (有 uv.lock), 默认源为清华镜像
- **Python >=3.12**, 使用 `list[X]` 等新式泛型语法

## Agent 图流程

```
extract_keywords → (recall_column | recall_value | recall_metric) → merge_retrieved_info
→ (filter_table | filter_metric) → add_extra_context → generate_sql
→ validate_sql → (correct_sql →) run_sql → END
```

## 依赖服务 (docker compose)

| 服务 | 端口 | 说明 |
|---|---|---|
| Elasticsearch | 9200 | 全文检索 (IK 分词) |
| Kibana | 5601 | ES 管理界面 |
| Qdrant | 6333(HTTP), 6334(gRPC) | 向量数据库 |
| Embedding (TEI) | 8081 | HuggingFace 文本向量化 |
