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
NAVIGATION_PROMPT = """Task: {instruction}
Context: {memory}

Return ONLY valid JSON (no markdown, no extra text). Rules:
- If reached_goal is false, goal_direction.distance MUST be > 0.
- distance is in meters; azimuth is in degrees.

{{
  "goal_direction": {{"azimuth": 0, "distance": 3}},
  "obstacles": [{{"distance": 2.0}}],
  "confidence": 0.0,
  "reached_goal": false
}}"""


class VLLMClient:
    """vLLM异步客户端（OpenAI兼容API）"""

    def __init__(self, api_url: str = None):
        self.api_url = api_url or settings.VLLM_API_URL
        self.model_name = "qwen3-vl"
        self.timeout = 30.0
        self._client = httpx.AsyncClient(timeout=self.timeout)

    def _encode_image(self, image: np.ndarray) -> str:
        """将numpy图像编码为base64"""
        # 转换为PIL Image
        img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=settings.VLLM_IMAGE_JPEG_QUALITY)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{img_str}"

    @staticmethod
    def _to_data_url_from_b64(frame_b64: str) -> str:
        return f"data:image/jpeg;base64,{frame_b64}"

    def _build_prompt(self, instruction: str, memory: str) -> str:
        return NAVIGATION_PROMPT.format(
            instruction=instruction,
            memory=memory or "none",
        )

    async def aclose(self):
        """关闭http客户端连接（可选，便于优雅退出）"""
        await self._client.aclose()

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
        image_url = self._encode_image(image)
        return await self._analyze_image_url(image_url=image_url, instruction=instruction, memory=memory)

    async def analyze_frame_b64(
        self, frame_b64: str, instruction: str, memory: str = ""
    ) -> Optional[VLLMResponse]:
        """直接使用浏览器上传的JPEG base64做推理，避免后端解码/重编码开销"""
        image_url = self._to_data_url_from_b64(frame_b64)
        return await self._analyze_image_url(image_url=image_url, instruction=instruction, memory=memory)

    async def _analyze_image_url(
        self, image_url: str, instruction: str, memory: str = ""
    ) -> Optional[VLLMResponse]:
        try:
            prompt = self._build_prompt(instruction=instruction, memory=memory)

            # 调用vLLM API (OpenAI格式)
            response = await self._client.post(
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
                    "max_tokens": settings.VLLM_MAX_TOKENS,
                    "temperature": 0.0,
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
            response = await self._client.get(f"{self.api_url}/health", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False


# 导入cv2（用于颜色转换）
import cv2
