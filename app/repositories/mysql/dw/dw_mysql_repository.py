from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import DBInfoState


class DWMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_column_types(self, table_name) -> dict[str, str]:
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        result_dict = result.mappings().fetchall()
        # [{Field:order_id,Type:varchar(30),Null:No},{Field:customer_id,Type:varchar(20),Null:YES}]

        return {row['Field']: row['Type'] for row in result_dict}
        # {order_id:varchar(30),customer_id:varchar(30)}

    async def get_column_values(self, table_name, column_name, limit=10):
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return [row[0] for row in result.fetchall()]

    async def get_db_info(self) -> DBInfoState:
        sql = "select version()"
        result = await self.session.execute(text(sql))
        version = result.scalar()

        dialect = self.session.bind.dialect.name

        return DBInfoState(dialect=dialect, version=version)

    async def validate(self, sql: str):
        sql = f"explain {sql}"
        await self.session.execute(text(sql))
