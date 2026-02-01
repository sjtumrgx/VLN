#!/usr/bin/env python3
"""Initialize SQLite database"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.storage.sqlite_client import SQLiteClient
from backend.config import settings


async def main():
    print("=" * 50)
    print("初始化VLN系统数据库")
    print("=" * 50)

    client = SQLiteClient(settings.SQLITE_DB_PATH)
    await client.init_db()

    print(f"✓ 数据库初始化完成: {settings.SQLITE_DB_PATH}")
    print(f"  - tasks 表创建")
    print(f"  - trajectories 表创建")
    print(f"  - 索引创建完成")


if __name__ == "__main__":
    asyncio.run(main())
