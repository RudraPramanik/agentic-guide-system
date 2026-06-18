import asyncio

from sqlalchemy import text

from src.core.database.session import get_engine


async def main():
    engine = get_engine()
    async with engine.connect() as conn:
        row = (await conn.execute(text("SELECT version()"))).fetchone()
        print(f"  Connected: {row[0][:60]}...")
        db = (await conn.execute(text("SELECT current_database()"))).fetchone()
        print(f"  Database:  {db[0]}")
        pool = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database()"
                )
            )
        ).fetchone()
        print(f"  Active connections: {pool[0]}")
    await engine.dispose()
    print("  Pool OK — connection test passed")


if __name__ == "__main__":
    asyncio.run(main())
