#!/usr/bin/env python3
"""诊断视频推理pipeline的每一层"""

import asyncio
import sys
from pathlib import Path

import numpy as np
import httpx

sys.path.insert(0, str(Path(__file__).parent))

from backend.config import settings
from backend.services.vllm_client import VLLMClient


async def check_layer_1_vllm_service():
    """Layer 1: 检查vLLM服务是否运行"""
    print("=" * 60)
    print("Layer 1: vLLM服务状态检查")
    print("=" * 60)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 检查健康状态
            print(f"\n检查: {settings.VLLM_API_URL}/health")
            response = await client.get(f"{settings.VLLM_API_URL}/health")
            print(f"✓ 健康检查: HTTP {response.status_code}")

            # 检查模型列表
            print(f"\n检查: {settings.VLLM_API_URL}/v1/models")
            response = await client.get(f"{settings.VLLM_API_URL}/v1/models")
            if response.status_code == 200:
                models = response.json()
                print(f"✓ 可用模型: {models}")
                return True
            else:
                print(f"✗ 获取模型列表失败: HTTP {response.status_code}")
                return False

    except Exception as e:
        print(f"✗ vLLM服务不可达: {e}")
        print("\n解决方案:")
        print("  1. 确认vLLM服务是否运行: bash scripts/start_vllm.sh")
        print("  2. 检查端口8000是否被占用: lsof -i :8000")
        print("  3. 查看vLLM日志获取详细错误")
        return False


async def check_layer_2_vllm_inference():
    """Layer 2: 测试vLLM推理功能"""
    print("\n" + "=" * 60)
    print("Layer 2: vLLM推理测试")
    print("=" * 60)

    client = VLLMClient()

    # 创建测试图像（640x480纯色）
    test_image = np.full((480, 640, 3), [50, 100, 150], dtype=np.uint8)

    print(f"\n发送测试图像到vLLM...")
    print(f"  图像尺寸: {test_image.shape}")
    print(f"  指令: '向前移动'")
    print(f"  vLLM URL: {settings.VLLM_API_URL}")

    try:
        import time
        start = time.time()

        result = await client.analyze_frame(
            image=test_image,
            instruction="向前移动",
            memory=""
        )

        latency = time.time() - start

        if result:
            print(f"\n✓ vLLM推理成功 (耗时: {latency*1000:.0f}ms)")
            print(f"  空间分析: {result.spatial_analysis[:80]}...")
            print(f"  推荐动作: {result.action}")
            print(f"  置信度: {result.confidence:.2f}")
            return True
        else:
            print(f"\n✗ vLLM推理失败")
            print("\n可能原因:")
            print("  1. vLLM API返回非200状态码")
            print("  2. vLLM API超时（>30秒）")
            print("  3. 模型输出格式不正确")
            print("\n调试步骤:")
            print("  1. 查看后端日志中的详细错误信息")
            print("  2. 手动测试vLLM API:")
            print(f"     curl {settings.VLLM_API_URL}/v1/chat/completions \\")
            print("       -H 'Content-Type: application/json' \\")
            print("       -d '{\"model\": \"qwen3-vl\", \"messages\": [...]}'")
            return False

    except Exception as e:
        print(f"\n✗ 推理异常: {e}")
        import traceback
        traceback.print_exc()
        return False


async def check_layer_3_backend_api():
    """Layer 3: 检查后端API"""
    print("\n" + "=" * 60)
    print("Layer 3: 后端API状态检查")
    print("=" * 60)

    backend_url = f"http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 健康检查
            print(f"\n检查: {backend_url}/api/health/")
            response = await client.get(f"{backend_url}/api/health/")
            if response.status_code == 200:
                health = response.json()
                print(f"✓ 后端健康状态: {health}")
                return True
            else:
                print(f"✗ 后端健康检查失败: HTTP {response.status_code}")
                return False

    except Exception as e:
        print(f"✗ 后端不可达: {e}")
        print("\n解决方案:")
        print("  1. 确认后端服务是否运行: bash scripts/start_backend.sh")
        print(f"  2. 检查端口{settings.BACKEND_PORT}是否被占用")
        return False


async def check_layer_4_websocket():
    """Layer 4: WebSocket端点检查"""
    print("\n" + "=" * 60)
    print("Layer 4: WebSocket端点检查")
    print("=" * 60)

    ws_url = f"ws://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}/ws/video"

    print(f"\nWebSocket端点: {ws_url}")
    print("说明: WebSocket连接需要通过前端浏览器测试")
    print("\n在浏览器控制台中检查:")
    print("  1. 打开开发者工具 (F12)")
    print("  2. 查看Network标签 -> WS过滤器")
    print("  3. 检查WebSocket连接状态")
    print("  4. 查看Console中是否有'WebSocket 连接成功'消息")

    return True


def print_troubleshooting_guide():
    """打印故障排查指南"""
    print("\n" + "=" * 60)
    print("常见问题排查指南")
    print("=" * 60)

    print("\n问题A: vLLM服务不可达")
    print("-" * 40)
    print("症状: Layer 1失败")
    print("检查:")
    print("  1. vLLM进程是否运行: ps aux | grep vllm")
    print("  2. GPU是否有足够显存: nvidia-smi")
    print("  3. 端口8000是否监听: netstat -tlnp | grep 8000")
    print("解决:")
    print("  bash scripts/start_vllm.sh  # 或 start_vllm_3gpu.sh")

    print("\n问题B: vLLM推理失败")
    print("-" * 40)
    print("症状: Layer 1通过但Layer 2失败")
    print("检查:")
    print("  1. 后端日志中的详细错误: vLLM API错误 / JSON解析失败")
    print("  2. vLLM服务日志中的错误")
    print("  3. 模型是否正确加载")

    print("\n问题C: 后端API不可达")
    print("-" * 40)
    print("症状: Layer 3失败")
    print("检查:")
    print("  1. 后端进程是否运行: ps aux | grep uvicorn")
    print("  2. 端口8001是否监听: netstat -tlnp | grep 8001")
    print("解决:")
    print("  bash scripts/start_backend.sh")

    print("\n问题D: WebSocket连接失败")
    print("-" * 40)
    print("症状: 前端显示WS: OFFLINE")
    print("检查:")
    print("  1. 前端代码中的WebSocket URL是否正确")
    print("  2. 如果使用端口转发，是否转发了8001端口")
    print("  3. 浏览器控制台中的WebSocket错误信息")
    print("解决:")
    print("  - 本地访问: ws://localhost:8001/ws/video")
    print("  - 端口转发: 确保转发 -L 8001:localhost:8001")

    print("\n问题E: 视频帧发送但无推理结果")
    print("-" * 40)
    print("症状: WebSocket连接正常，但Canvas黑屏")
    print("检查:")
    print("  1. 后端日志中是否有'处理视频帧'相关消息")
    print("  2. 是否有任何Python异常")
    print("  3. vLLM推理是否超时")
    print("调试:")
    print("  - 在后端日志中查找具体错误")
    print("  - 检查浏览器Console中是否收到navigation_result消息")
    print("  - 运行本诊断脚本的Layer 2测试vLLM推理")


async def main():
    print("VLN系统诊断工具")
    print("=" * 60)
    print(f"配置信息:")
    print(f"  vLLM URL: {settings.VLLM_API_URL}")
    print(f"  后端地址: {settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
    print("=" * 60)

    results = {}

    # 逐层检查
    results['vllm_service'] = await check_layer_1_vllm_service()

    if results['vllm_service']:
        results['vllm_inference'] = await check_layer_2_vllm_inference()
    else:
        print("\n⚠ 跳过Layer 2: vLLM服务未运行")
        results['vllm_inference'] = False

    results['backend_api'] = await check_layer_3_backend_api()
    results['websocket'] = await check_layer_4_websocket()

    # 总结
    print("\n" + "=" * 60)
    print("诊断结果汇总")
    print("=" * 60)

    all_passed = all(results.values())

    for layer, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{layer:20s}: {status}")

    if all_passed:
        print("\n🎉 所有检查通过！系统应该可以正常工作。")
        print("\n如果前端仍然黑屏，请检查:")
        print("  1. 浏览器控制台是否有JavaScript错误")
        print("  2. 是否成功创建了任务（发布任务按钮点击后）")
        print("  3. 视频是否正在播放（不是暂停状态）")
    else:
        print("\n⚠ 发现问题，请参考下方故障排查指南")
        print_troubleshooting_guide()


if __name__ == "__main__":
    asyncio.run(main())
