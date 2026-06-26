# Data Agent

基于 LangGraph 的自然语言数据查询 Agent，将中文问题自动转化为 SQL 并在数据仓库中执行。

## 架构

用户输入中文查询 → FastAPI → LangGraph Agent（多节点 DAG 流程）→ SQL 执行 → 流式返回结果

Agent 经过关键词提取、向量/全文检索、表/指标过滤、SQL 生成与校验等节点，最终在数据仓库中执行 SQL。

## 技术栈

| 层 | 技术 |
|---|---|
| 框架 | FastAPI + LangGraph |
| Agent | LangGraph DAG, 12 个节点 |
| LLM | langchain `init_chat_model` (兼容 OpenAI/DashScope) |
| Embedding | DashScope API |
| 向量库 | Qdrant |
| 全文检索 | Elasticsearch (IK 分词) |
| 数据库 | MySQL × 2 (meta 元数据库 + dw 数据仓库) |
| 前端 | 独立 Vue.js 项目 (`data-agent-fronted/`) |
| 包管理 | uv, 清华镜像源 |

## 前置依赖

- Python >=3.12
- Docker (ES, Qdrant, Kibana)
- MySQL × 2 (meta 库 + dw 库)
- `.env` 文件：`DASHSCOPE_API_KEY=sk-xxx`

## 快速开始

```bash
# 1. 启动依赖服务
cd docker && docker-compose up -d

# 2. 配置
cp conf/app_config.yaml conf/app_config.yaml  # 编辑数据库密码和 LLM API key
echo "DASHSCOPE_API_KEY=sk-xxx" > .env

# 3. 构建元数据知识（将 MySQL 表结构同步到 Qdrant + ES）
uv run python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml

# 4. 启动 API
uv run python main.py

# 5. 查询
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "查询华北地区的销售总额"}'
```

## Agent 流程

```
extract_keywords ─┬→ recall_column ─┐
                  ├→ recall_value ──┤
                  └→ recall_metric ─┘
                          ↓
                  merge_retrieved_info
                     ↙            ↘
              filter_table    filter_metric
                     ↘            ↙
                  add_extra_context
                         ↓
                   generate_sql
                         ↓
                   validate_sql ─→ correct_sql
                         ↓              ↓
                      run_sql ←─────────┘
                         ↓
                        END
```

## 项目结构

```
app/
  agent/          # LangGraph 图定义 + 节点实现
  api/            # FastAPI 路由、依赖注入、Pydantic schema
  clients/        # 外部服务连接管理（单例模式）
  conf/           # OmegaConf 配置 schema（dataclass）
  core/           # 日志（loguru）和请求上下文
  entities/       # 业务实体（dataclass）
  models/         # SQLAlchemy ORM 模型
  repositories/   # 数据访问层（Mapper 模式）
  scripts/        # 可执行脚本
  services/       # 业务逻辑服务
conf/             # YAML 配置文件
prompts/          # LLM 提示词模板（.prompt 文件）
docker/           # docker-compose + 服务定制
```

## 配置

`conf/app_config.yaml` 包含数据库密码和 LLM API key，**不提交到 Git**。配置通过 OmegaConf 加载，由 `app/conf/app_config.py` 中的 dataclass schema 校验。

## 关键命令

```bash
uv run python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml  # 构建元数据
uv run python -m app.agent.graph          # 测试 Agent（硬编码查询）
uv run python -m app.agent.llm            # 测试 LLM 连接
uv run python main.py                     # 启动 API
```
