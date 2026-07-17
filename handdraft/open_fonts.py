from __future__ import annotations

import json
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = PROJECT_ROOT / "data" / "fonts"
LICENSE_DIR = FONT_DIR / "licenses"
MANIFEST_PATH = FONT_DIR / "downloaded-open-fonts.json"

OPEN_FONTS = [
    {
        "family": "Xiaolai",
        "filename": "Xiaolai-Regular.ttf",
        "url": "https://github.com/lxgw/kose-font/releases/download/v3.126/Xiaolai-Regular.ttf",
        "license_url": "https://raw.githubusercontent.com/lxgw/kose-font/main/OFL.txt",
        "license": "SIL Open Font License 1.1",
        "style": "normal neat handwritten",
        "category": "normal",
    },
    {
        "family": "LXGW WenKai",
        "filename": "LXGWWenKai-Regular.ttf",
        "url": "https://github.com/lxgw/LxgwWenKai/releases/download/v1.522/LXGWWenKai-Regular.ttf",
        "license_url": "https://raw.githubusercontent.com/lxgw/LxgwWenKai/main/OFL.txt",
        "license": "SIL Open Font License 1.1",
        "style": "regular pen handwriting",
        "category": "normal",
    },
    {
        "family": "Liu Jian Mao Cao",
        "filename": "LiuJianMaoCao-Regular.ttf",
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/liujianmaocao/LiuJianMaoCao-Regular.ttf",
        "license_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/liujianmaocao/OFL.txt",
        "license": "SIL Open Font License 1.1",
        "style": "cursive narrow fast",
        "category": "cursive",
    },
    {
        "family": "Zhi Mang Xing",
        "filename": "ZhiMangXing-Regular.ttf",
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/zhimangxing/ZhiMangXing-Regular.ttf",
        "license_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/zhimangxing/OFL.txt",
        "license": "SIL Open Font License 1.1",
        "style": "connected homework style",
        "category": "cursive",
    },
    {
        "family": "Long Cang",
        "filename": "LongCang-Regular.ttf",
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/longcang/LongCang-Regular.ttf",
        "license_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/longcang/OFL.txt",
        "license": "SIL Open Font License 1.1",
        "style": "loose semi-cursive",
        "category": "cursive",
    },
    {
        "family": "Ma Shan Zheng",
        "filename": "MaShanZheng-Regular.ttf",
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/mashanzheng/MaShanZheng-Regular.ttf",
        "license_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/mashanzheng/OFL.txt",
        "license": "SIL Open Font License 1.1",
        "style": "brush handwriting",
        "category": "cursive",
    },
    {
        "family": "ZCOOL KuaiLe",
        "filename": "ZCOOLKuaiLe-Regular.ttf",
        "url": "https://raw.githubusercontent.com/google/fonts/main/ofl/zcoolkuaile/ZCOOLKuaiLe-Regular.ttf",
        "license_url": "https://raw.githubusercontent.com/google/fonts/main/ofl/zcoolkuaile/OFL.txt",
        "license": "SIL Open Font License 1.1",
        "style": "casual handwritten title",
        "category": "title",
    },
]


def _download(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=45) as response:
        data = response.read()
    if len(data) < 1024:
        raise RuntimeError(f"downloaded file is unexpectedly small: {url}")
    target.write_bytes(data)


def downloaded_manifest() -> dict[str, dict[str, str]]:
    if not MANIFEST_PATH.exists():
        return {}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def download_open_fonts(force: bool = False, categories: set[str] | None = None) -> dict[str, object]:
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = downloaded_manifest()
    installed: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []

    for font in OPEN_FONTS:
        if categories and font["category"] not in categories:
            continue
        font_target = FONT_DIR / font["filename"]
        license_target = LICENSE_DIR / f"{Path(font['filename']).stem}-OFL.txt"
        already_installed = font_target.exists() and license_target.exists()
        try:
            if force or not font_target.exists():
                _download(font["url"], font_target)
            if force or not license_target.exists():
                _download(font["license_url"], license_target)
        except Exception as exc:
            font_target.unlink(missing_ok=True)
            failed.append({"family": font["family"], "error": type(exc).__name__})
            continue
        manifest[font["filename"]] = {
            "family": font["family"],
            "license": font["license"],
            "license_file": str(license_target.relative_to(PROJECT_ROOT)),
            "source": font["url"],
            "style": font["style"],
            "category": font["category"],
        }
        item = {
            "family": font["family"],
            "filename": font["filename"],
            "license": font["license"],
            "style": font["style"],
            "category": font["category"],
        }
        (skipped if already_installed and not force else installed).append(item)

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "installed": installed,
        "already_installed": skipped,
        "failed": failed,
        "manifest": str(MANIFEST_PATH.relative_to(PROJECT_ROOT)),
    }


def list_open_font_manifest() -> list[dict[str, str]]:
    manifest = downloaded_manifest()
    return [{"filename": name, **data} for name, data in manifest.items()]
