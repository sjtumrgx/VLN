"""Model management API endpoints"""

from fastapi import APIRouter

from backend.config import settings

router = APIRouter(tags=["models"])

# 支持的模型列表
AVAILABLE_MODELS = {
    "qwen3-vl-8b": {
        "name": "Qwen3-VL-8B-Instruct",
        "path": "/data1/Qwen3VL/models--Qwen--Qwen3-VL-8B-Instruct",
        "description": "8B parameter model, fast inference",
    },
    "qwen3-vl-30b": {
        "name": "Qwen3-VL-30B-A3B-Instruct",
        "path": "/data1/Qwen3VL/models--Qwen--Qwen3-VL-30B-A3B-Instruct",
        "description": "30B parameter MoE model, higher quality",
    },
}


@router.get("/list")
async def list_models():
    """列出可用模型"""
    return {
        "models": AVAILABLE_MODELS,
        "current": settings.DEFAULT_MODEL,
    }


@router.get("/status")
async def model_status():
    """获取模型加载状态"""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.VLLM_API_URL}/health")
            if resp.status_code == 200:
                return {"status": "loaded", "url": settings.VLLM_API_URL}
    except Exception:
        pass

    return {"status": "not_loaded", "url": settings.VLLM_API_URL}
