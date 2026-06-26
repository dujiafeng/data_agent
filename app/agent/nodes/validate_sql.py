from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.core.log import logger

async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "校验SQL", "status": "running"})

    sql = state['sql']
    dw_mysql_repository: DWMySQLRepository = runtime.context["dw_mysql_repository"]

    try:
        await dw_mysql_repository.validate(sql)
        logger.info("SQL语法正确")
        writer({"type": "progress", "step": "校验SQL", "status": "success"})
        return {'error': None}
    except Exception as e:
        logger.info(f"SQL语法错误：{str(e)}")
        writer({"type": "progress", "step": "校验SQL", "status": "error"})
        return {'error': str(e)}
