import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio.engine import AsyncEngine, create_async_engine

from app.conf.app_config import DBConfig, app_config


class MySQlClientManager:
    def __init__(self, config: DBConfig):
        self.config = config
        self.engine: AsyncEngine | None = None

    def _get_url(self):
        return f"mysql+asyncmy://{self.config.user}:{self.config.password}@{self.config.host}:{self.config.port}/{self.config.database}?charset=utf8mb4"

    def init(self):
        self.engine = create_async_engine(self._get_url(), pool_size=10, pool_pre_ping=True)

    async def close(self):
        await self.engine.dispose()


mete_mysql_client_manager = MySQlClientManager(app_config.db_meta)
dw_mysql_client_manager = MySQlClientManager(app_config.db_dw)

if __name__ == '__main__':
    dw_mysql_client_manager.init()

    engine = dw_mysql_client_manager.engine


    async def test():
        async with AsyncSession(engine) as session:
            sql = "select * from fact_order limit 10"
            result = await session.execute(text(sql))

            rows = result.fetchall()

            print(type(rows))
            print(type(rows[0]))
            print(rows)

    asyncio.run(test())
