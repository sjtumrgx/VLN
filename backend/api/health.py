"""FastAPI health check endpoint"""

from fastapi import APIRouter

from backend.config import settings

router = APIRouter(tags=["health"])


@router.get("/")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "VLN System"}


@router.get("/config")
async def get_config():
    """获取当前配置（非敏感信息）"""
    return {
        "default_model": settings.DEFAULT_MODEL,
        "video_resolution": settings.video_resolution,
        "inference_fps": settings.VIDEO_INFERENCE_FPS,
        "num_waypoints": settings.NUM_WAYPOINTS,
        "vllm_max_tokens": settings.VLLM_MAX_TOKENS,
        "vllm_image_jpeg_quality": settings.VLLM_IMAGE_JPEG_QUALITY,
    }
