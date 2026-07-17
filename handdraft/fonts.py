from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Iterable

from .open_fonts import OPEN_FONTS, downloaded_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
USER_FONT_DIR = PROJECT_ROOT / "data" / "fonts"
FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}

REFERENCE_FONT_METADATA: dict[str, dict[str, str]] = {
    "李国夫手写体.ttf": {"family": "李国夫手写体", "style": "日常硬笔手写", "category": "normal"},
    "青叶手写体.ttf": {"family": "青叶手写体", "style": "轻盈日常手写", "category": "normal"},
    "国祥手写体v2.0.ttf": {"family": "国祥手写体", "style": "自然硬笔手写", "category": "normal"},
    "戴锦好字体.ttf": {"family": "戴锦好手写体", "style": "清晰硬笔手写", "category": "normal"},
    "义启手写体.ttf": {"family": "义启手写体", "style": "随笔手写", "category": "normal"},
    "立夏手写体.ttf": {"family": "立夏手写体", "style": "工整日常手写", "category": "normal"},
}


def _system_font_dirs() -> list[Path]:
    dirs: list[Path] = [USER_FONT_DIR]
    windir = os.environ.get("WINDIR")
    if windir:
        dirs.append(Path(windir) / "Fonts")
    dirs.extend(
        [
            Path("C:/Windows/Fonts"),
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path("/Library/Fonts"),
            Path.home() / "Library" / "Fonts",
        ]
    )
    seen: set[Path] = set()
    unique: list[Path] = []
    for item in dirs:
        try:
            resolved = item.resolve()
        except OSError:
            resolved = item
        if resolved not in seen:
            seen.add(resolved)
            unique.append(item)
    return unique


def _font_id(path: Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode("utf-8")).hexdigest()[:20]


def _is_recommended(path: Path) -> bool:
    name = path.name.lower()
    hints = (
        "xiaolai",
        "lxgwwenkai",
        "liujianmaocao",
        "zhimangxing",
        "longcang",
        "mashanzheng",
        "zcoolkuaile",
        "kai",
        "kaiti",
        "xing",
        "script",
        "hand",
        "wenkai",
        "fangsong",
        "simkai",
        "stkaiti",
        "stxingka",
        "simsun",
        "msyh",
    )
    return any(hint in name for hint in hints)


def iter_font_paths() -> Iterable[Path]:
    for directory in _system_font_dirs():
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in FONT_EXTENSIONS:
                yield path


def list_fonts() -> list[dict[str, object]]:
    fonts = []
    open_manifest = downloaded_manifest()
    catalog = {item["filename"]: item for item in OPEN_FONTS}
    for path in iter_font_paths():
        if USER_FONT_DIR in path.parents and path.name in REFERENCE_FONT_METADATA:
            source = "reference"
        elif USER_FONT_DIR in path.parents and path.name in open_manifest:
            source = "open"
        elif USER_FONT_DIR in path.parents:
            source = "user"
        else:
            source = "system"
        open_info = {
            **catalog.get(path.name, {}),
            **open_manifest.get(path.name, {}),
            **REFERENCE_FONT_METADATA.get(path.name, {}),
        }
        fonts.append(
            {
                "id": _font_id(path),
                "name": open_info.get("family") or path.stem,
                "filename": path.name,
                "source": source,
                "recommended": _is_recommended(path),
                "style": open_info.get("style", ""),
                "license": open_info.get("license")
                or ("Authorized; see data/fonts/REFERENCE-FONTS-SOURCE.md" if source == "reference" else ""),
                "category": open_info.get("category", ""),
            }
        )
    def category_rank(item: dict[str, object]) -> int:
        category = str(item.get("category", ""))
        if category == "normal":
            return 0
        if item["source"] == "user":
            return 1
        if category:
            return 2
        return 3

    source_rank = {"reference": 0, "open": 1, "user": 2, "system": 3}
    reference_rank = {filename: index for index, filename in enumerate(REFERENCE_FONT_METADATA)}
    fonts.sort(
        key=lambda item: (
            category_rank(item),
            source_rank.get(str(item["source"]), 9),
            reference_rank.get(str(item["filename"]), 99),
            not item["recommended"],
            str(item["name"]).lower(),
        )
    )
    return fonts


def resolve_font(font_id: str) -> Path | None:
    if not font_id:
        return find_default_font()
    for path in iter_font_paths():
        if _font_id(path) == font_id:
            return path
    return None


def find_default_font() -> Path | None:
    paths = list(iter_font_paths())
    if not paths:
        return None
    preferred_names = (
        "李国夫手写体",
        "青叶手写体",
        "国祥手写体",
        "戴锦好字体",
        "义启手写体",
        "立夏手写体",
        "xiaolai-regular",
        "lxgwwenkai-regular",
        "xiaolai",
        "lxgwwenkai",
        "zcoolkuaile",
        "zhimangxing",
        "liujianmaocao",
        "longcang",
        "mashanzheng",
        "simkai",
        "stkaiti",
        "stxingka",
        "kaiti",
        "kai",
        "fangsong",
        "simsun",
        "msyh",
        "arial",
    )
    for hint in preferred_names:
        for path in paths:
            if hint in path.name.lower():
                return path
    return paths[0]
