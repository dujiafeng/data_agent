from datetime import datetime

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, DateInfoState
from app.core.log import logger

async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "补充额外上下文信息", "status": "running"})

    try:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        weekday_str = now.strftime("%A")
        month = now.month
        quarter = f"Q{(month - 1) // 3 + 1}"
        date_info = DateInfoState(date=date_str, weekday=weekday_str, quarter=quarter)

        dw_mysql_repository = runtime.context['dw_mysql_repository']
        db_info = await dw_mysql_repository.get_db_info()
        logger.info(f"数据库信息：{db_info}")
        logger.info(f"日期信息：{date_info}")

        writer({"type": "progress", "step": "补充额外上下文信息", "status": "success"})
        return {
            "date_info": date_info,
            "db_info": db_info
        }
    except Exception as e:
        logger.info(f"补充额外上下文信息失败: {e}")
        writer({"type": "progress", "step": "补充额外上下文信息", "status": "error"})
        raise
