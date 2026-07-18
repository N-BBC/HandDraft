from __future__ import annotations

import math
import json
import logging
import os
import shutil
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .document import DocumentError, extract_text
from .fonts import FONT_EXTENSIONS, find_default_font, list_fonts, resolve_font
from .open_fonts import OPEN_FONTS, download_open_fonts, list_open_font_manifest
from .renderer import RenderSettings, render_pages, save_outputs
from .security import install_log_redaction, redact_secret


install_log_redaction()
logger = logging.getLogger("handdraft")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = PROJECT_ROOT / "static"
DATA_DIR = PROJECT_ROOT / "data"
JOBS_DIR = DATA_DIR / "jobs"

MAX_DOCUMENT_BYTES = 18 * 1024 * 1024
MAX_ASSET_BYTES = 28 * 1024 * 1024
DEMO_MODE = os.getenv("HANDDRAFT_DEMO_MODE", "").lower() in {"1", "true", "yes", "on"}
JOB_TTL_SECONDS = max(300, int(os.getenv("HANDDRAFT_JOB_TTL_SECONDS", "3600")))
DEMO_RATE_LIMIT = max(1, int(os.getenv("HANDDRAFT_RATE_LIMIT", "6")))
DEMO_RATE_WINDOW_SECONDS = max(10, int(os.getenv("HANDDRAFT_RATE_WINDOW_SECONDS", "60")))
DEMO_MAX_PAGES = max(1, int(os.getenv("HANDDRAFT_MAX_PAGES", "6")))

if DEMO_MODE:
    MAX_DOCUMENT_BYTES = min(MAX_DOCUMENT_BYTES, 6 * 1024 * 1024)
    MAX_ASSET_BYTES = min(MAX_ASSET_BYTES, 12 * 1024 * 1024)


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> tuple[bool, int]:
        current = time.monotonic() if now is None else now
        with self._lock:
            events = self._events[key]
            cutoff = current - self.window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                retry_after = max(1, math.ceil(events[0] + self.window_seconds - current))
                return False, retry_after
            events.append(current)
            return True, 0


def cleanup_expired_jobs(
    jobs_dir: Path = JOBS_DIR,
    max_age_seconds: int = JOB_TTL_SECONDS,
    now: float | None = None,
) -> int:
    current = time.time() if now is None else now
    removed = 0
    if not jobs_dir.exists():
        return removed
    for child in jobs_dir.iterdir():
        if not child.is_dir():
            continue
        try:
            if current - child.stat().st_mtime > max_age_seconds:
                shutil.rmtree(child)
                removed += 1
        except FileNotFoundError:
            continue
    return removed


@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_expired_jobs()
    yield


demo_limiter = SlidingWindowLimiter(DEMO_RATE_LIMIT, DEMO_RATE_WINDOW_SECONDS)

app = FastAPI(title="HandDraft", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=JOBS_DIR), name="outputs")


@app.middleware("http")
async def public_demo_guards(request: Request, call_next):
    if DEMO_MODE and request.method == "POST" and request.url.path == "/api/render":
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        client_ip = forwarded or (request.client.host if request.client else "unknown")
        allowed, retry_after = demo_limiter.allow(client_ip)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "生成请求过于频繁，请稍后再试。"},
                headers={"Retry-After": str(retry_after)},
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


def _safe_name(filename: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    name = "".join(ch if ch in allowed else "_" for ch in Path(filename).name)
    return name or f"upload-{uuid.uuid4().hex}"


async def _save_upload(upload: UploadFile, directory: Path, max_bytes: int) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / _safe_name(upload.filename or "upload")
    total = 0
    with target.open("wb") as handle:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                handle.close()
                target.unlink(missing_ok=True)
                await upload.close()
                raise HTTPException(status_code=413, detail="上传文件过大。")
            handle.write(chunk)
    await upload.close()
    return target


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, object]:
    visible_fonts = [
        font for font in list_fonts() if font.get("category") == "normal" or font.get("source") == "user"
    ]
    return {
        "ok": True,
        "fonts": len(visible_fonts),
        "demo_mode": DEMO_MODE,
        "retention_minutes": JOB_TTL_SECONDS // 60 if DEMO_MODE else None,
    }


@app.get("/api/fonts")
def fonts() -> dict[str, object]:
    items = list_fonts()
    default = find_default_font()
    return {
        "fonts": items,
        "default_id": next((item["id"] for item in items if default and item["filename"] == default.name), None),
    }


@app.get("/api/fonts/{font_id}/file")
def font_file(font_id: str) -> FileResponse:
    path = resolve_font(font_id)
    if not path:
        raise HTTPException(status_code=404, detail="字体不存在。")
    media_types = {".ttf": "font/ttf", ".otf": "font/otf", ".ttc": "font/collection"}
    return FileResponse(path, media_type=media_types.get(path.suffix.lower(), "application/octet-stream"))


@app.get("/api/open-fonts")
def open_fonts() -> dict[str, object]:
    return {"available": OPEN_FONTS, "installed": list_open_font_manifest()}


@app.post("/api/open-fonts/download")
def download_fonts() -> dict[str, object]:
    if DEMO_MODE:
        raise HTTPException(status_code=403, detail="在线演示已内置字体，不支持下载新字体。")
    result = download_open_fonts(force=False, categories={"normal"})
    return {"ok": not result["failed"], **result, "fonts": list_fonts()}


@app.post("/api/render")
async def render(
    document: Annotated[UploadFile, File()],
    settings: Annotated[str, Form()] = "{}",
    font_id: Annotated[str, Form()] = "",
    background: Annotated[UploadFile | None, File()] = None,
    scene_background: Annotated[UploadFile | None, File()] = None,
    font_upload: Annotated[UploadFile | None, File()] = None,
) -> dict[str, object]:
    cleanup_expired_jobs()
    job_id = uuid.uuid4().hex
    job_dir = JOBS_DIR / job_id
    upload_dir = job_dir / "uploads"
    job_dir.mkdir(parents=True, exist_ok=True)

    document_path = await _save_upload(document, upload_dir, MAX_DOCUMENT_BYTES)
    suffix = document_path.suffix.lower()
    if suffix not in {".md", ".markdown", ".txt", ".doc", ".docx"}:
        raise HTTPException(status_code=400, detail="文档格式不支持，请上传 .md、.txt、.docx 或可转换的 .doc。")

    background_path = None
    if background and background.filename:
        background_path = await _save_upload(background, upload_dir, MAX_ASSET_BYTES)

    scene_background_path = None
    if scene_background and scene_background.filename:
        scene_background_path = await _save_upload(scene_background, upload_dir, MAX_ASSET_BYTES)

    font_path = None
    if font_upload and font_upload.filename:
        if Path(font_upload.filename).suffix.lower() not in FONT_EXTENSIONS:
            raise HTTPException(status_code=400, detail="字体格式不支持，请上传 .ttf、.otf 或 .ttc。")
        font_path = await _save_upload(font_upload, upload_dir, MAX_ASSET_BYTES)
    else:
        font_path = resolve_font(font_id)

    if not font_path:
        raise HTTPException(status_code=400, detail="没有找到可用字体，请上传 .ttf/.otf/.ttc 字体。")

    try:
        text = extract_text(document_path)
        if not text.strip():
            raise DocumentError("文档里没有可渲染的文字。")
        render_settings = RenderSettings.from_payload(settings)
        if DEMO_MODE:
            render_settings.max_pages = min(render_settings.max_pages, DEMO_MAX_PAGES)
        pages = render_pages(text, font_path, background_path, render_settings, scene_background_path)
        outputs = save_outputs(pages, job_dir)
    except DocumentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("render failed")
        raise HTTPException(status_code=500, detail="渲染失败，请检查文档、背景或字体文件。") from exc

    page_files = outputs["page_files"]
    return {
        "job_id": job_id,
        "page_count": len(page_files),
        "pages": [{"name": name, "url": f"/outputs/{job_id}/{name}"} for name in page_files],
        "pdf_url": f"/outputs/{job_id}/{outputs['pdf']}",
        "zip_url": f"/outputs/{job_id}/{outputs['zip']}",
    }


@app.post("/api/ai/glyph-kit")
async def glyph_kit(payload: Annotated[dict[str, object], Body()]) -> dict[str, object]:
    if DEMO_MODE:
        raise HTTPException(status_code=403, detail="在线演示不接收 API Key，请在本地运行后使用。")
    api_key = str(payload.get("apiKey") or payload.get("api_key") or "")
    provider = str(payload.get("provider") or "custom")
    model = str(payload.get("model") or "")
    if not api_key:
        raise HTTPException(status_code=400, detail="请填写 API Key。")

    # The key intentionally stays in request memory only. It is not written to disk,
    # not echoed back, and not used until a concrete provider adapter is added.
    return {
        "status": "planned",
        "provider": provider,
        "model": model,
        "key_hint": redact_secret(api_key),
        "message": "字迹库生成接口已预留；当前 MVP 不会发起外部模型请求。",
    }
