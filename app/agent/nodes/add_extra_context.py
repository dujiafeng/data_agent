from datetime import datetime

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, DateInfoState
from app.core.log import logger

async def add_extra_context(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer("添加额外上下文")

    now = datetime.now()
    # 1. 日期字符串（格式：YYYY-MM-DD）
    date_str = now.strftime("%Y-%m-%d")
    # 2. 星期几（英文全称，如 "Monday"）
    #    若设置了中文 locale，则为 "星期一"
    weekday_str = now.strftime("%A")
    # 3. 季度（计算规则：1-3月→Q1, 4-6→Q2, ...）
    month = now.month
    quarter = f"Q{(month - 1) // 3 + 1}"
    date_info = DateInfoState(date=date_str, weekday=weekday_str, quarter=quarter)

    dw_mysql_repository = runtime.context['dw_mysql_repository']
    db_info = await dw_mysql_repository.get_db_info()
    logger.info(f"数据库信息：{db_info}")
    logger.info(f"日期信息：{date_info}")

    return {
        "date_info": date_info,
        "db_info": db_info
    }
