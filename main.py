import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ---------- 1. 创建异步引擎和 Session ----------
# 使用 SQLite 内存数据库（方便测试），实际使用时替换为真实连接串
DATABASE_URL = "'mysql+asyncmy://atguigu:Atguigu.123@localhost:3306/dw?charset=utf8mb4'"  # 异步 SQLite 驱动
# 若使用 PostgreSQL: "postgresql+asyncpg://user:pass@localhost/db"
# 若使用 MySQL:      "mysql+aiomysql://user:pass@localhost/db"

engine = create_async_engine(DATABASE_URL, echo=True)  # echo=True 可查看执行的 SQL

# 创建异步 Session 工厂，默认 autobegin=True（自动开始事务）
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# ---------- 2. 定义获取数据库信息的函数 ----------
async def inspect_database(session: AsyncSession) -> dict:
    """
    通过异步会话获取数据库类型和版本信息。
    """
    # 2.1 从引擎获取方言名称和驱动
    dialect = session.bind.dialect.name   # 如 'sqlite', 'postgresql', 'mysql'
    driver = session.bind.driver          # 如 'aiosqlite', 'asyncpg', 'aiomysql'

    # 2.2 根据方言选择版本查询语句
    version_query_map = {
        'postgresql': "SELECT VERSION()",
        'mysql':      "SELECT VERSION()",
        'sqlite':     "SELECT sqlite_version()",
        'mssql':      "SELECT @@VERSION"
    }
    sql_text = version_query_map.get(dialect, "SELECT 'Unknown'")  # 默认返回 Unknown

    # 2.3 执行查询（必须处于活跃事务中）
    # 使用 async with session.begin() 确保事务已开启（即使 autobegin=False 也安全）
    async with session.begin():
        result = await session.execute(text(sql_text))
        version = result.scalar()  # 取第一行第一列

    return {
        "dialect": dialect,
        "driver": driver,
        "version": version
    }


# ---------- 3. 主异步函数 ----------
async def main():
    # 创建一个 Session 实例
    async with AsyncSessionLocal() as session:
        # 调用检测函数
        info = await inspect_database(session)
        print("\n========== 数据库连接信息 ==========")
        print(f"数据库类型 (Dialect): {info['dialect']}")
        print(f"驱动 (Driver):        {info['driver']}")
        print(f"版本 (Version):       {info['version']}")
        print("====================================\n")

    # 关闭引擎（释放资源）
    await engine.dispose()


# ---------- 4. 运行 ----------
if __name__ == "__main__":
    asyncio.run(main())