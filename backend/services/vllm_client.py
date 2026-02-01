"""vLLM client for Qwen3-VL inference"""

import base64
import json
import logging
from io import BytesIO
from typing import Optional

import httpx
import numpy as np
from PIL import Image

from backend.config import settings
from backend.models.navigation import VLLMResponse

logger = logging.getLogger(__name__)

# Prompt模板
NAVIGATION_PROMPT = """You are a navigation assistant for a quadruped robot.

Task: {instruction}

Previous context: {memory}

Analyze the current view and provide navigation guidance.
Your response MUST be valid JSON in this exact format:
{{
  "spatial_analysis": "描述当前场景的空间理解",
  "action": "move_forward|turn_left|turn_right|reached_goal",
  "goal_direction": {{"azimuth": 45, "distance": 3.5}},
  "obstacles": [
    {{"type": "wall", "position": "left", "distance": 2.0}},
    {{"type": "furniture", "position": "front-right", "distance": 1.5}}
  ],
  "confidence": 0.85,
  "reached_goal": false
}}

CRITICAL: Output ONLY valid JSON, no additional text before or after."""


class VLLMClient:
    """vLLM异步客户端（OpenAI兼容API）"""

    def __init__(self, api_url: str = None):
        self.api_url = api_url or settings.VLLM_API_URL
        self.model_name = "qwen3-vl"
        self.timeout = 30.0

    def _encode_image(self, image: np.ndarray) -> str:
        """将numpy图像编码为base64"""
        # 转换为PIL Image
        img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"

    async def analyze_frame(
        self, image: np.ndarray, instruction: str, memory: str = ""
    ) -> Optional[VLLMResponse]:
        """
        分析视频帧并返回导航指令

        Args:
            image: 输入图像 (numpy array, BGR格式)
            instruction: 用户指令
            memory: 历史记忆摘要

        Returns:
            VLLMResponse or None if error
        """
        try:
            # 编码图像
            image_url = self._encode_image(image)

            # 构造prompt
            prompt = NAVIGATION_PROMPT.format(
                instruction=instruction, memory=memory or "无历史记录"
            )

            # 调用vLLM API (OpenAI格式)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.api_url}/v1/chat/completions",
                    json={
                        "model": self.model_name,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": image_url}},
                                ],
                            }
                        ],
                        "max_tokens": 512,
                        "temperature": 0.1,
                    },
                )

                if response.status_code != 200:
                    logger.error(f"vLLM API错误: {response.status_code} - {response.text}")
                    return None

                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # 解析JSON响应
                try:
                    # 尝试提取JSON（防止模型输出多余文本）
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        content = content[json_start:json_end]

                    parsed = json.loads(content)
                    return VLLMResponse(**parsed)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON解析失败: {e}\n内容: {content}")
                    # 返回默认响应
                    return VLLMResponse(
                        spatial_analysis="无法解析模型输出",
                        action="move_forward",
                        confidence=0.0,
                    )

        except httpx.TimeoutException:
            logger.error("vLLM请求超时")
            return None
        except Exception as e:
            logger.error(f"vLLM推理错误: {e}")
            return None

    async def check_health(self) -> bool:
        """检查vLLM服务健康状态"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.api_url}/health")
                return response.status_code == 200
        except Exception:
            return False


# 导入cv2（用于颜色转换）
import cv2
