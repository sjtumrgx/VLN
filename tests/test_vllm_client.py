"""测试vLLM客户端（需要vLLM服务运行）"""

import sys
import asyncio
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.vllm_client import VLLMClient


async def test_vllm_connection():
    """测试vLLM服务连接"""
    print("=== 测试vLLM连接 ===\n")

    client = VLLMClient()

    # 检查健康状态
    is_healthy = await client.check_health()

    if is_healthy:
        print("✓ vLLM服务运行正常")
    else:
        print("✗ vLLM服务未运行")
        print("  请先启动vLLM: bash scripts/start_vllm.sh")
        return False

    return True


async def test_vllm_inference():
    """测试vLLM推理（需要服务运行）"""
    print("\n=== 测试vLLM推理 ===\n")

    client = VLLMClient()

    # 检查服务
    if not await client.check_health():
        print("✗ vLLM服务未运行，跳过推理测试")
        return

    # 创建测试图像（纯色图）
    test_image = np.full((480, 640, 3), [50, 50, 100], dtype=np.uint8)

    print("发送测试图像到vLLM...")
    result = await client.analyze_frame(
        image=test_image,
        instruction="向前移动到门口",
        memory="无历史记录"
    )

    if result:
        print(f"✓ 推理成功")
        print(f"  空间分析: {result.spatial_analysis[:50]}...")
        print(f"  推荐动作: {result.action}")
        print(f"  置信度: {result.confidence:.2f}")
        print(f"  目标方向: 方位角{result.goal_direction.get('azimuth', 0)}°, "
              f"距离{result.goal_direction.get('distance', 0):.1f}m")
    else:
        print("✗ 推理失败")


async def test_vllm_latency():
    """测试推理延迟"""
    print("\n=== 测试推理延迟 ===\n")

    client = VLLMClient()

    if not await client.check_health():
        print("✗ vLLM服务未运行，跳过延迟测试")
        return

    import time

    test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    latencies = []
    num_tests = 3

    print(f"运行 {num_tests} 次推理测试...")

    for i in range(num_tests):
        start = time.time()
        result = await client.analyze_frame(test_image, "测试", "")
        latency = time.time() - start
        latencies.append(latency)
        print(f"  第{i+1}次: {latency*1000:.0f}ms")

    avg_latency = sum(latencies) / len(latencies)
    print(f"\n平均延迟: {avg_latency*1000:.0f}ms")
    print(f"预估FPS: {1/avg_latency:.1f}")

    if avg_latency < 0.5:
        print("✓ 延迟表现优秀（<500ms）")
    elif avg_latency < 1.0:
        print("⚠ 延迟可接受（500-1000ms）")
    else:
        print("✗ 延迟较高（>1000ms），建议优化")


async def main():
    connected = await test_vllm_connection()

    if connected:
        await test_vllm_inference()
        await test_vllm_latency()
        print("\n✅ vLLM测试完成！")
    else:
        print("\n⚠ vLLM服务未运行，部分测试跳过")


if __name__ == "__main__":
    asyncio.run(main())
