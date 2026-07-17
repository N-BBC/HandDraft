from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
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

app = FastAPI(title="HandDraft", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/outputs", StaticFiles(directory=JOBS_DIR), name="outputs")


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
    return {"ok": True, "fonts": len(visible_fonts)}


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
