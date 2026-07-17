from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from handdraft.document import extract_text
from handdraft.fonts import find_default_font
from handdraft.renderer import RenderSettings, render_pages, save_outputs


def main() -> None:
    sample = ROOT / "samples" / "sample.md"
    text = extract_text(sample)
    assert "手写转换测试" in text
    assert "支持列表" in text

    font = find_default_font()
    if font is None:
        raise RuntimeError("没有找到系统字体，请上传或安装一个 .ttf/.otf/.ttc 字体后再试。")

    settings = RenderSettings(font_size=34, line_height=58, max_pages=3, seed=123, scene_mode="scan")
    pages = render_pages(text, font, None, settings)
    assert pages, "没有生成页面"
    assert pages[0].size[0] >= 640 and pages[0].size[1] >= 900

    tmp = Path(tempfile.mkdtemp(prefix="handdraft-smoke-"))
    try:
        outputs = save_outputs(pages, tmp)
        assert (tmp / outputs["pdf"]).exists()
        assert (tmp / outputs["zip"]).exists()
        first_page = tmp / outputs["page_files"][0]
        assert first_page.exists()
        with Image.open(first_page) as image:
            assert image.size == pages[0].size
            grayscale = image.convert("L")
            pixels = grayscale.get_flattened_data() if hasattr(grayscale, "get_flattened_data") else grayscale.getdata()
            dark_pixels = sum(1 for pixel in pixels if pixel < 130)
            assert dark_pixels > 200, "输出页看起来没有文字"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("smoke test passed")


if __name__ == "__main__":
    main()
