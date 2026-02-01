"""测试REST API端点"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx


BASE_URL = "http://localhost:8001"


async def test_health():
    """测试健康检查"""
    print("=== 测试健康检查 ===\n")

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/api/health/")
        print(f"状态码: {resp.status_code}")
        print(f"响应: {resp.json()}")
        assert resp.status_code == 200
        print("✓ 健康检查通过")


async def test_task_crud():
    """测试任务CRUD操作"""
    print("\n=== 测试任务CRUD ===\n")

    async with httpx.AsyncClient() as client:
        # 创建任务
        print("创建任务...")
        resp = await client.post(
            f"{BASE_URL}/api/tasks/create",
            json={"instruction": "去厨房拿一杯水"}
        )
        print(f"  状态码: {resp.status_code}")
        assert resp.status_code == 200
        task = resp.json()
        task_id = task["id"]
        print(f"  ✓ 任务创建成功: {task_id[:8]}...")

        # 查询任务
        print("查询任务...")
        resp = await client.get(f"{BASE_URL}/api/tasks/{task_id}")
        assert resp.status_code == 200
        task = resp.json()
        assert task["instruction"] == "去厨房拿一杯水"
        print(f"  ✓ 查询成功: {task['instruction']}")

        # 更新任务
        print("更新任务状态...")
        resp = await client.patch(
            f"{BASE_URL}/api/tasks/{task_id}",
            json={"status": "running"}
        )
        assert resp.status_code == 200
        print("  ✓ 更新成功")

        # 获取任务列表
        print("获取任务列表...")
        resp = await client.get(f"{BASE_URL}/api/tasks/list?limit=10")
        assert resp.status_code == 200
        tasks = resp.json()
        print(f"  ✓ 共 {len(tasks)} 个任务")

        print("\n✅ 任务CRUD测试通过！")


async def test_model_api():
    """测试模型API"""
    print("\n=== 测试模型API ===\n")

    async with httpx.AsyncClient() as client:
        # 获取模型列表
        resp = await client.get(f"{BASE_URL}/api/models/list")
        print(f"模型列表: {resp.json()}")
        assert resp.status_code == 200
        print("✓ 模型列表获取成功")

        # 获取模型状态
        resp = await client.get(f"{BASE_URL}/api/models/status")
        print(f"模型状态: {resp.json()}")
        assert resp.status_code == 200
        print("✓ 模型状态获取成功")


async def main():
    try:
        await test_health()
        await test_task_crud()
        await test_model_api()
        print("\n" + "=" * 50)
        print("✅ 所有API测试通过！")
        print("=" * 50)
    except httpx.ConnectError:
        print("✗ 无法连接到后端服务")
        print("  请先启动后端: bash scripts/start_backend.sh")
    except AssertionError as e:
        print(f"✗ 测试失败: {e}")
    except Exception as e:
        print(f"✗ 测试异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())
