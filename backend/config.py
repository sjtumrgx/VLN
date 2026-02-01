"""
配置管理模块
使用pydantic-settings从环境变量加载配置
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Tuple


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 模型配置
    MODEL_PATH: str = Field(
        default="/data1/Qwen3VL/models--Qwen--Qwen3-VL-8B-Instruct",
        description="Qwen3-VL模型路径",
    )
    DEFAULT_MODEL: str = Field(default="qwen3-vl-8b", description="默认模型名称")

    # 服务配置
    VLLM_API_URL: str = Field(default="http://localhost:8000", description="vLLM API地址")
    BACKEND_HOST: str = Field(default="0.0.0.0", description="后端服务监听地址")
    BACKEND_PORT: int = Field(default=8001, description="后端服务端口")

    # Redis配置
    REDIS_URL: str = Field(default="redis://localhost:6379", description="Redis连接URL")
    REDIS_DB: int = Field(default=0, description="Redis数据库编号")

    # SQLite配置
    SQLITE_DB_PATH: str = Field(default="./data/vln.db", description="SQLite数据库路径")

    # 性能配置
    VIDEO_INFERENCE_FPS: int = Field(default=5, description="视频推理帧率")
    VIDEO_STREAM_RESOLUTION_WIDTH: int = Field(default=384, description="视频流宽度")
    VIDEO_STREAM_RESOLUTION_HEIGHT: int = Field(default=288, description="视频流高度")
    FRAME_SKIP_RATIO: int = Field(default=3, description="帧跳过比率")
    WEBSOCKET_MAX_QUEUE_SIZE: int = Field(default=5, description="WebSocket最大队列大小")
    GPU_MEMORY_UTILIZATION: float = Field(default=0.95, description="GPU显存利用率")
    TENSOR_PARALLEL_SIZE: int = Field(default=4, description="张量并行大小")

    # vLLM推理参数
    VLLM_MAX_TOKENS: int = Field(default=128, description="vLLM生成token上限（越小越快）")
    VLLM_IMAGE_JPEG_QUALITY: int = Field(default=65, description="发送到vLLM的JPEG质量(1-100)")

    # 路径规划配置
    NUM_WAYPOINTS: int = Field(default=12, description="航点数量")
    MAX_LINEAR_VELOCITY: float = Field(default=1.0, description="最大线速度 (m/s)")
    MAX_ANGULAR_VELOCITY: float = Field(default=1.57, description="最大角速度 (rad/s)")

    # 记忆配置
    MEMORY_WINDOW_SIZE: int = Field(default=10, description="记忆窗口大小")
    MEMORY_SUMMARY_LENGTH: int = Field(default=5, description="记忆摘要长度")

    @property
    def video_resolution(self) -> Tuple[int, int]:
        """返回视频分辨率元组 (width, height)"""
        return (self.VIDEO_STREAM_RESOLUTION_WIDTH, self.VIDEO_STREAM_RESOLUTION_HEIGHT)


# 全局配置实例
settings = Settings()
