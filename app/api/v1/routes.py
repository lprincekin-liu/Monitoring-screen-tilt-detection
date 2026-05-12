from __future__ import annotations

import logging
import time
from json import JSONDecodeError

import psutil
from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError

from app.core.config import get_settings, reload_settings
from app.core.gpu import get_gpu_status
from app.core.state import app_state
from app.schemas.tilt import ErrorResponse, TiltRequest, TiltResponse
from app.services.tilt_detector import detect_from_base64


router = APIRouter()
logger = logging.getLogger(__name__)


def _format_elapsed(seconds: float) -> str:
    return f"{int(seconds // 3600)}h {int((seconds % 3600) // 60)}m {int(seconds % 60)}s"


def _detect(req: TiltRequest) -> TiltResponse:
    settings = get_settings()
    start_time = time.time()
    result = detect_from_base64(
        req.image_base64,
        settings.detection,
        settings.runtime.max_image_bytes,
    )
    cost_ms = round((time.time() - start_time) * 1000, 2)
    app_state.increment_requests()
    return TiltResponse(
        code=200,
        is_tilted=result.is_tilted,
        angle=round(result.angle, 2),
        cost_ms=cost_ms,
        msg=result.message,
    )


async def _parse_tilt_request(request: Request) -> TiltRequest:
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        if isinstance(payload, dict):
            return TiltRequest(**payload)
        if isinstance(payload, str):
            return TiltRequest(image_base64=payload)

    body = (await request.body()).decode("utf-8").strip()
    if not body:
        raise ValueError("Request body is empty")
    return TiltRequest(image_base64=body)


@router.post(
    "/detect_tilt",
    response_model=TiltResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def detect_tilt_async(request: Request) -> TiltResponse:
    try:
        req = await _parse_tilt_request(request)
        return await run_in_threadpool(_detect, req)
    except (JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail={"code": 400, "msg": str(exc)})
    except Exception as exc:
        logger.exception("Async tilt detection failed")
        raise HTTPException(
            status_code=500, detail={"code": 500, "msg": f"Detection failed: {exc}"}
        )


@router.post(
    "/detect_tilt/sync",
    response_model=TiltResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def detect_tilt_sync(request: Request) -> TiltResponse:
    try:
        req = await _parse_tilt_request(request)
        return _detect(req)
    except (JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail={"code": 400, "msg": str(exc)})
    except Exception as exc:
        logger.exception("Sync tilt detection failed")
        raise HTTPException(
            status_code=500, detail={"code": 500, "msg": f"Detection failed: {exc}"}
        )


@router.get("/health")
async def health_check() -> dict:
    settings = get_settings()
    elapsed = time.time() - app_state.start_time
    process = psutil.Process()
    return {
        "status": "success",
        "elapsed_time": _format_elapsed(elapsed),
        "total_requests": app_state.request_count,
        "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
        "gpu": get_gpu_status(
            settings.gpu.enabled,
            settings.gpu.require_gpu,
            settings.gpu.device_id,
        ).as_dict(),
    }


@router.get("/config")
async def get_runtime_config() -> dict:
    settings = get_settings()
    return {
        "app": settings.app.__dict__,
        "server": settings.server.__dict__,
        "gpu": settings.gpu.__dict__,
        "detection": settings.detection.__dict__,
        "runtime": settings.runtime.__dict__,
    }


@router.post("/config/reload")
async def reload_runtime_config() -> dict:
    settings = reload_settings()
    return {
        "code": 200,
        "msg": "Config reloaded",
        "detection": settings.detection.__dict__,
    }
