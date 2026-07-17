from __future__ import annotations

import json
import random
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont


PAPER_TEMPLATE_CONFIG: dict[str, dict[str, object]] = {
    "photo_blank": {
        "filenames": ("desk-reference-local.jpg", "papers/reference-blank-desk.jpg"),
        "margins": (0.12, 0.10, 0.10, 0.08),
    },
    "reference_blank_desk": {
        "filenames": ("papers/reference-blank-desk.jpg",),
        "margins": (0.12, 0.10, 0.10, 0.08),
    },
    "reference_blank_warm": {
        "filenames": ("papers/reference-blank-warm.jpg",),
        "margins": (0.12, 0.10, 0.10, 0.08),
    },
    "reference_blank_cool": {
        "filenames": ("papers/reference-blank-cool.jpg",),
        "margins": (0.12, 0.10, 0.10, 0.08),
    },
    "reference_blank_mono": {
        "filenames": ("papers/reference-blank-mono.jpg",),
        "margins": (0.12, 0.10, 0.10, 0.08),
    },
    "reference_lined_photo": {
        "filenames": ("papers/reference-lined-photo.jpg",),
        "margins": (0.06, 0.04, 0.05, 0.03),
    },
    "reference_lined_clean": {
        "filenames": ("papers/reference-lined-clean.jpg",),
        "margins": (0.105, 0.0825, 0.04, 0.09),
    },
    "reference_notebook": {
        "filenames": ("papers/reference-notebook.jpg",),
        "margins": (0.06, 0.06, 0.045, 0.035),
    },
    "reference_report_body": {
        "filenames": ("papers/reference-report-body.jpg",),
        "margins": (0.065, 0.04, 0.15, 0.045),
    },
    "reference_report_cover": {
        "filenames": ("papers/reference-report-cover.jpg",),
        "margins": (0.10, 0.075, 0.57, 0.065),
    },
}


def _clamp(value: Any, low: float, high: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def _parse_color(value: str | None) -> tuple[int, int, int]:
    if not value:
        return (30, 33, 34)
    color = value.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    if len(color) != 6:
        return (30, 33, 34)
    try:
        return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return (30, 33, 34)


@dataclass
class RenderSettings:
    page_width: int = 1240
    page_height: int = 1754
    use_background_size: bool = True
    background_fit: str = "cover"
    direct_background: bool = False
    paper_style: str = "photo_blank"
    margin_left: int = 90
    margin_right: int = 70
    margin_top: int = 96
    margin_bottom: int = 88
    font_size: int = 42
    line_height: int = 68
    char_spacing: float = 0.5
    paragraph_spacing: int = 12
    position_jitter: float = 0.7
    rotation_jitter: float = 0.7
    size_jitter: float = 0.5
    opacity_jitter: float = 0.06
    ink_color: tuple[int, int, int] = (30, 33, 34)
    seed: int = 17
    max_pages: int = 12
    glyph_width_jitter: float = 0.035
    glyph_height_jitter: float = 0.025
    slant_jitter: float = 0.025
    baseline_jitter: float = 0.9
    line_start_jitter: float = 8.0
    line_slope_jitter: float = 0.003
    line_wave_jitter: float = 0.6
    correction_rate: float = 0.0
    ink_density: float = 0.92
    style_profile: str = "clean"
    scene_mode: str = "desk_photo"
    scene_width: int = 1080
    scene_height: int = 1920

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | str | None) -> "RenderSettings":
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        payload = payload or {}
        return cls(
            page_width=int(_clamp(payload.get("page_width"), 640, 3200, cls.page_width)),
            page_height=int(_clamp(payload.get("page_height"), 900, 4200, cls.page_height)),
            use_background_size=bool(payload.get("use_background_size", True)),
            background_fit=str(payload.get("background_fit") or "cover"),
            direct_background=bool(payload.get("direct_background", False)),
            paper_style=str(payload.get("paper_style") or "photo_blank"),
            margin_left=int(_clamp(payload.get("margin_left"), 0, 1600, cls.margin_left)),
            margin_right=int(_clamp(payload.get("margin_right"), 0, 1600, cls.margin_right)),
            margin_top=int(_clamp(payload.get("margin_top"), 0, 3000, cls.margin_top)),
            margin_bottom=int(_clamp(payload.get("margin_bottom"), 0, 3000, cls.margin_bottom)),
            font_size=int(_clamp(payload.get("font_size"), 10, 160, cls.font_size)),
            line_height=int(_clamp(payload.get("line_height"), 16, 240, cls.line_height)),
            char_spacing=_clamp(payload.get("char_spacing"), -12, 40, cls.char_spacing),
            paragraph_spacing=int(_clamp(payload.get("paragraph_spacing"), 0, 160, cls.paragraph_spacing)),
            position_jitter=_clamp(payload.get("position_jitter"), 0, 18, cls.position_jitter),
            rotation_jitter=_clamp(payload.get("rotation_jitter"), 0, 18, cls.rotation_jitter),
            size_jitter=_clamp(payload.get("size_jitter"), 0, 16, cls.size_jitter),
            opacity_jitter=_clamp(payload.get("opacity_jitter"), 0, 0.55, cls.opacity_jitter),
            ink_color=_parse_color(payload.get("ink_color")),
            seed=int(_clamp(payload.get("seed"), 0, 999999, cls.seed)),
            max_pages=int(_clamp(payload.get("max_pages"), 1, 40, cls.max_pages)),
            glyph_width_jitter=_clamp(payload.get("glyph_width_jitter"), 0, 0.5, cls.glyph_width_jitter),
            glyph_height_jitter=_clamp(payload.get("glyph_height_jitter"), 0, 0.35, cls.glyph_height_jitter),
            slant_jitter=_clamp(payload.get("slant_jitter"), 0, 0.5, cls.slant_jitter),
            baseline_jitter=_clamp(payload.get("baseline_jitter"), 0, 22, cls.baseline_jitter),
            line_start_jitter=_clamp(payload.get("line_start_jitter"), 0, 100, cls.line_start_jitter),
            line_slope_jitter=_clamp(payload.get("line_slope_jitter"), 0, 0.12, cls.line_slope_jitter),
            line_wave_jitter=_clamp(payload.get("line_wave_jitter"), 0, 18, cls.line_wave_jitter),
            correction_rate=_clamp(payload.get("correction_rate"), 0, 0.18, cls.correction_rate),
            ink_density=_clamp(payload.get("ink_density"), 0.25, 1.0, cls.ink_density),
            style_profile=str(payload.get("style_profile") or cls.style_profile),
            scene_mode=str(payload.get("scene_mode") or cls.scene_mode),
            scene_width=int(_clamp(payload.get("scene_width"), 720, 1800, cls.scene_width)),
            scene_height=int(_clamp(payload.get("scene_height"), 960, 2600, cls.scene_height)),
        )


def make_default_background(width: int, height: int, line_height: int, paper_style: str = "blank") -> Image.Image:
    base = Image.new("RGB", (width, height), (250, 248, 239))
    noise = Image.effect_noise((width, height), 7).convert("L")
    paper = Image.blend(base, Image.merge("RGB", (noise, noise, noise)), 0.035)
    draw = ImageDraw.Draw(paper)
    rng = random.Random(width * 131 + height * 17 + line_height)
    step = max(28, line_height)
    if paper_style in {"lined", "grid"}:
        for y in range(0, height, step):
            wobble = rng.randint(-2, 2)
            color = (214 + rng.randint(-4, 4), 224 + rng.randint(-4, 4), 222 + rng.randint(-4, 4))
            draw.line((0, y + wobble, width, y + wobble + rng.choice([-1, 0, 1])), fill=color, width=1)
    if paper_style == "grid":
        for x in range(0, width, step):
            draw.line((x, 0, x, height), fill=(224, 220, 210), width=1)
    if paper_style == "report":
        for y in range(0, height, step):
            draw.line((0, y, width, y), fill=(215, 224, 223), width=1)
        draw.line((int(width * 0.13), 0, int(width * 0.13), height), fill=(218, 145, 145), width=2)
    draw.rectangle((0, 0, width - 1, height - 1), outline=(228, 222, 207))
    return paper


def _paper_template_path(paper_style: str) -> Path | None:
    config = PAPER_TEMPLATE_CONFIG.get(paper_style)
    if not config:
        return None
    assets = Path(__file__).resolve().parents[1] / "static" / "assets"
    for filename in config["filenames"]:
        candidate = assets / str(filename)
        if candidate.exists():
            return candidate
    return None


def fit_background(path: Path | None, settings: RenderSettings) -> Image.Image:
    width, height = settings.page_width, settings.page_height
    if not path:
        template_path = _paper_template_path(settings.paper_style)
        if template_path:
            source = Image.open(template_path).convert("RGB")
            width = settings.page_width
            height = int(round(width * source.height / source.width))
            settings.page_height = height
            return source.resize((width, height), Image.Resampling.LANCZOS)
        return make_default_background(width, height, settings.line_height, settings.paper_style)

    background = Image.open(path).convert("RGB")
    if settings.use_background_size:
        width, height = background.size
        scale = min(
            1.0,
            3200 / max(1, width),
            4200 / max(1, height),
            (8_000_000 / max(1, width * height)) ** 0.5,
        )
        if scale < 1.0:
            width = int(width * scale)
            height = int(height * scale)
            background = background.resize((width, height), Image.Resampling.LANCZOS)
        settings.page_width = width
        settings.page_height = height
        return background

    target = (width, height)
    if settings.background_fit == "stretch":
        return background.resize(target, Image.Resampling.LANCZOS)
    if settings.background_fit == "contain":
        canvas = make_default_background(width, height, settings.line_height, settings.paper_style)
        background.thumbnail(target, Image.Resampling.LANCZOS)
        x = (width - background.width) // 2
        y = (height - background.height) // 2
        canvas.paste(background, (x, y))
        return canvas

    src_ratio = background.width / background.height
    dst_ratio = width / height
    if src_ratio > dst_ratio:
        new_height = height
        new_width = int(height * src_ratio)
    else:
        new_width = width
        new_height = int(width / src_ratio)
    resized = background.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = (new_width - width) // 2
    top = (new_height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _font_for_size(font_path: Path, size: int, cache: dict[int, ImageFont.FreeTypeFont]) -> ImageFont.FreeTypeFont:
    size = max(6, size)
    if size not in cache:
        cache[size] = ImageFont.truetype(str(font_path), size=size)
    return cache[size]


def _text_width(font: ImageFont.FreeTypeFont, text: str) -> float:
    try:
        return float(font.getlength(text))
    except AttributeError:
        bbox = font.getbbox(text)
        return float(bbox[2] - bbox[0])


def _deform_glyph(glyph: Image.Image, rng: random.Random, settings: RenderSettings) -> Image.Image:
    if settings.style_profile not in {"draft", "rough"}:
        return glyph

    width_scale = 1 + rng.uniform(-settings.glyph_width_jitter, settings.glyph_width_jitter * 0.35)
    height_scale = 1 + rng.uniform(-settings.glyph_height_jitter, settings.glyph_height_jitter)
    resized = glyph.resize(
        (max(1, int(glyph.width * width_scale)), max(1, int(glyph.height * height_scale))),
        Image.Resampling.BICUBIC,
    )
    skew = rng.uniform(-settings.slant_jitter, settings.slant_jitter)
    x_shift = abs(skew) * resized.height
    skewed_width = max(1, int(resized.width + x_shift))
    offset = x_shift if skew > 0 else 0
    return resized.transform(
        (skewed_width, resized.height),
        Image.Transform.AFFINE,
        (1, -skew, offset, 0, 1, 0),
        resample=Image.Resampling.BICUBIC,
    )


def _draw_correction(
    page: Image.Image,
    char: str,
    font: ImageFont.FreeTypeFont,
    x: float,
    y: float,
    width: float,
    rng: random.Random,
    settings: RenderSettings,
) -> None:
    draw = ImageDraw.Draw(page)
    color = (*settings.ink_color, int(210 * settings.ink_density))
    mid_y = y + settings.font_size * rng.uniform(0.55, 0.82)
    draw.line(
        (
            x + rng.uniform(-2, 2),
            mid_y + rng.uniform(-2, 2),
            x + width + rng.uniform(-1, 4),
            mid_y + rng.uniform(-2, 2),
        ),
        fill=color,
        width=max(1, int(settings.font_size / 22)),
    )
    small_size = max(8, int(settings.font_size * 0.54))
    try:
        small_font = font.font_variant(size=small_size)
    except Exception:
        small_font = font
    draw.text((x + width * 0.2, y - small_size * 0.55), char, font=small_font, fill=color)


def _draw_glyph(
    page: Image.Image,
    char: str,
    font: ImageFont.FreeTypeFont,
    x: float,
    y: float,
    rng: random.Random,
    settings: RenderSettings,
) -> None:
    bbox = font.getbbox(char)
    width = max(1, bbox[2] - bbox[0])
    height = max(1, bbox[3] - bbox[1])
    pad = max(8, int(settings.font_size * 0.35))
    glyph = Image.new("RGBA", (width + pad * 2, height + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glyph)
    opacity = int(255 * settings.ink_density * (1 - rng.uniform(0, settings.opacity_jitter)))
    fill = (*settings.ink_color, max(20, min(255, opacity)))
    draw.text((pad - bbox[0], pad - bbox[1]), char, font=font, fill=fill)

    glyph = _deform_glyph(glyph, rng, settings)
    angle = rng.uniform(-settings.rotation_jitter, settings.rotation_jitter)
    rotated = glyph.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    dx = rng.uniform(-settings.position_jitter, settings.position_jitter)
    dy = rng.uniform(-settings.baseline_jitter, settings.baseline_jitter)
    page.alpha_composite(rotated, (int(x + dx - pad), int(y + dy - pad)))

    if settings.correction_rate and rng.random() < settings.correction_rate and char.strip():
        _draw_correction(page, char, font, x, y, width, rng, settings)


def _find_perspective_coeffs(destination: list[tuple[float, float]], source: list[tuple[float, float]]) -> list[float]:
    matrix: list[list[float]] = []
    vector: list[float] = []
    for (x, y), (u, v) in zip(destination, source):
        matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        vector.extend([u, v])

    n = 8
    for col in range(n):
        pivot = max(range(col, n), key=lambda row: abs(matrix[row][col]))
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        vector[col], vector[pivot] = vector[pivot], vector[col]
        div = matrix[col][col] or 1e-12
        matrix[col] = [value / div for value in matrix[col]]
        vector[col] /= div
        for row in range(n):
            if row == col:
                continue
            factor = matrix[row][col]
            matrix[row] = [value - factor * matrix[col][idx] for idx, value in enumerate(matrix[row])]
            vector[row] -= factor * vector[col]
    return vector


def _make_desk(width: int, height: int, rng: random.Random) -> Image.Image:
    desk = Image.new("RGB", (width, height), (178, 136, 82))
    noise = Image.effect_noise((width, height), 22).convert("L")
    desk = Image.blend(desk, Image.merge("RGB", (noise, noise, noise)), 0.08)
    draw = ImageDraw.Draw(desk)
    for y in range(-40, height, 54):
        color = (145 + rng.randint(-10, 12), 103 + rng.randint(-8, 8), 62 + rng.randint(-6, 8))
        draw.line((0, y + rng.randint(-10, 10), width, y + rng.randint(-10, 10)), fill=color, width=rng.randint(1, 3))
    for _ in range(48):
        x = rng.randint(0, width)
        y = rng.randint(0, height)
        shade = rng.randint(68, 110)
        draw.ellipse((x, y, x + rng.randint(2, 6), y + rng.randint(2, 7)), fill=(shade, shade // 2, shade // 3))

    laptop = Image.new("RGBA", (int(width * 0.64), int(height * 0.25)), (25, 31, 42, 245))
    laptop_draw = ImageDraw.Draw(laptop)
    laptop_draw.rounded_rectangle((0, 0, laptop.width - 1, laptop.height - 1), radius=18, outline=(45, 52, 62), width=4)
    laptop = laptop.rotate(-4, expand=True, resample=Image.Resampling.BICUBIC)
    desk.paste(laptop, (int(width * 0.34), int(height * 0.06)), laptop)

    stack = Image.new("RGBA", (int(width * 0.5), int(height * 0.18)), (238, 238, 236, 250))
    stack_draw = ImageDraw.Draw(stack)
    stack_draw.rectangle((0, stack.height - 14, stack.width, stack.height - 8), fill=(210, 210, 205, 220))
    stack = stack.rotate(8, expand=True, resample=Image.Resampling.BICUBIC)
    desk.paste(stack, (int(width * 0.03), int(height * 0.01)), stack)

    drive = Image.new("RGBA", (int(width * 0.25), int(height * 0.08)), (220, 212, 190, 245))
    drive_draw = ImageDraw.Draw(drive)
    drive_draw.rounded_rectangle((0, 0, drive.width - 1, drive.height - 1), radius=8, outline=(180, 170, 150), width=2)
    drive = drive.rotate(12, expand=True, resample=Image.Resampling.BICUBIC)
    desk.paste(drive, (int(width * 0.74), int(height * 0.17)), drive)
    return desk.filter(ImageFilter.GaussianBlur(0.25))


def _default_scene_path() -> Path | None:
    assets = Path(__file__).resolve().parents[1] / "static" / "assets"
    for filename in ("desk-reference-local.jpg", "desk-photo-v2.jpg"):
        candidate = assets / filename
        if candidate.exists():
            return candidate
    return None


def _make_scene_background(width: int, height: int, rng: random.Random, scene_background_path: Path | None) -> Image.Image:
    if scene_background_path is None:
        scene_background_path = _default_scene_path()
    if scene_background_path:
        source = Image.open(scene_background_path).convert("RGB")
        src_ratio = source.width / source.height
        dst_ratio = width / height
        if src_ratio > dst_ratio:
            new_height = height
            new_width = int(height * src_ratio)
        else:
            new_width = width
            new_height = int(width / src_ratio)
        resized = source.resize((new_width, new_height), Image.Resampling.LANCZOS)
        left = (new_width - width) // 2
        top = (new_height - height) // 2
        scene = resized.crop((left, top, left + width, top + height))
        return scene.filter(ImageFilter.GaussianBlur(0.35))
    return _make_desk(width, height, rng)


def _perspective_layer(layer: Image.Image, quad: list[tuple[float, float]], scene_size: tuple[int, int]) -> Image.Image:
    source = [(0, 0), (layer.width, 0), (layer.width, layer.height), (0, layer.height)]
    coeffs = _find_perspective_coeffs(quad, source)
    return layer.transform(
        scene_size,
        Image.Transform.PERSPECTIVE,
        coeffs,
        Image.Resampling.BICUBIC,
        fillcolor=(0, 0, 0, 0),
    )


def compose_desk_photo(page: Image.Image, settings: RenderSettings, index: int, scene_background_path: Path | None = None) -> Image.Image:
    rng = random.Random(settings.seed + index * 7919)
    scene_size = (settings.scene_width, settings.scene_height)
    scene = _make_scene_background(*scene_size, rng, scene_background_path).convert("RGBA")
    effective_scene_path = scene_background_path or _default_scene_path()
    portrait_scene = False
    if effective_scene_path:
        with Image.open(effective_scene_path) as source:
            portrait_scene = source.height > source.width * 1.12

    width_range = (0.86, 0.9) if portrait_scene else (0.78, 0.84)
    target_w = int(settings.scene_width * rng.uniform(*width_range))
    target_h = int(target_w * page.height / page.width)
    if target_h > settings.scene_height * 0.78:
        target_h = int(settings.scene_height * 0.78)
        target_w = int(target_h * page.width / page.height)
    paper = page.resize((target_w, target_h), Image.Resampling.LANCZOS).convert("RGBA")

    if portrait_scene:
        x = int((settings.scene_width - target_w) / 2 + rng.uniform(-8, 8))
        y = int(settings.scene_height * 0.12 + rng.uniform(-10, 10))
        quad = [
            (x + rng.uniform(-5, 3), y + rng.uniform(2, 8)),
            (x + target_w + rng.uniform(-4, 6), y + rng.uniform(-4, 5)),
            (x + target_w + rng.uniform(-4, 6), y + target_h + rng.uniform(-3, 7)),
            (x + rng.uniform(-7, 4), y + target_h + rng.uniform(-5, 5)),
        ]
    else:
        x = int((settings.scene_width - target_w) / 2 + rng.uniform(-28, 20))
        y = int(settings.scene_height * 0.26 + rng.uniform(-30, 20))
        quad = [
            (x + rng.uniform(-16, 10), y + rng.uniform(0, 24)),
            (x + target_w + rng.uniform(-18, 20), y + rng.uniform(-12, 18)),
            (x + target_w + rng.uniform(-8, 22), y + target_h + rng.uniform(-10, 18)),
            (x + rng.uniform(-22, 12), y + target_h + rng.uniform(-18, 12)),
        ]

    shadow = Image.new("RGBA", paper.size, (0, 0, 0, 115))
    shadow_layer = _perspective_layer(shadow, [(px + 18, py + 24) for px, py in quad], scene_size)
    scene.alpha_composite(shadow_layer.filter(ImageFilter.GaussianBlur(20)))
    scene.alpha_composite(_perspective_layer(paper, quad, scene_size))

    vignette = Image.new("L", scene_size, 0)
    vd = ImageDraw.Draw(vignette)
    vd.ellipse(
        (-settings.scene_width * 0.25, -settings.scene_height * 0.15, settings.scene_width * 1.25, settings.scene_height * 1.18),
        fill=120,
    )
    vignette = ImageChops.invert(vignette.filter(ImageFilter.GaussianBlur(90)))
    dark = Image.new("RGBA", scene_size, (0, 0, 0, 35))
    dark.putalpha(vignette.point(lambda value: int(value * 0.2)))
    scene.alpha_composite(dark)
    scene = ImageEnhance.Color(scene.convert("RGB")).enhance(0.92)
    scene = ImageEnhance.Contrast(scene).enhance(1.04)
    return scene.filter(ImageFilter.GaussianBlur(0.25))


def render_pages(
    text: str,
    font_path: Path,
    background_path: Path | None,
    settings: RenderSettings,
    scene_background_path: Path | None = None,
) -> list[Image.Image]:
    background = fit_background(background_path, settings)
    width, height = background.size
    if settings.margin_left + settings.margin_right >= width:
        raise ValueError("左右边距之和必须小于页面宽度。")
    if settings.margin_top + settings.margin_bottom >= height:
        raise ValueError("上下边距之和必须小于页面高度。")
    max_x = width - settings.margin_right
    max_y = height - settings.margin_bottom
    rng = random.Random(settings.seed)
    font_cache: dict[int, ImageFont.FreeTypeFont] = {}
    base_font = _font_for_size(font_path, settings.font_size, font_cache)
    space_width = max(_text_width(base_font, " "), settings.font_size * 0.28)

    pages: list[Image.Image] = [background.convert("RGBA")]
    line_x_offset = rng.uniform(-settings.line_start_jitter, settings.line_start_jitter)
    line_slope = rng.uniform(-settings.line_slope_jitter, settings.line_slope_jitter)
    x = float(settings.margin_left + line_x_offset)
    y = float(settings.margin_top)

    def new_page() -> None:
        nonlocal x, y, line_x_offset, line_slope
        if len(pages) >= settings.max_pages:
            raise ValueError(f"内容超过最大页数限制（{settings.max_pages} 页）。")
        pages.append(background.copy().convert("RGBA"))
        line_x_offset = rng.uniform(-settings.line_start_jitter, settings.line_start_jitter)
        line_slope = rng.uniform(-settings.line_slope_jitter, settings.line_slope_jitter)
        x = float(settings.margin_left + line_x_offset)
        y = float(settings.margin_top)

    def new_line(extra: float = 0) -> None:
        nonlocal x, y, line_x_offset, line_slope
        line_x_offset = rng.uniform(-settings.line_start_jitter, settings.line_start_jitter)
        line_slope = rng.uniform(-settings.line_slope_jitter, settings.line_slope_jitter)
        x = float(settings.margin_left + line_x_offset)
        y += settings.line_height + extra + rng.uniform(-settings.line_wave_jitter, settings.line_wave_jitter)
        if y + settings.line_height > max_y:
            new_page()

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    for paragraph in normalized.split("\n"):
        if not paragraph.strip():
            new_line(settings.paragraph_spacing * 0.35)
            continue
        for char in paragraph:
            if char == " ":
                if x + space_width > max_x:
                    new_line()
                x += space_width + settings.char_spacing
                continue

            size = int(round(settings.font_size + rng.uniform(-settings.size_jitter, settings.size_jitter)))
            font = _font_for_size(font_path, size, font_cache)
            char_width = max(_text_width(font, char), size * 0.34)
            if x + char_width > max_x and x > settings.margin_left:
                new_line()
            slope_y = y + (x - settings.margin_left) * line_slope
            _draw_glyph(pages[-1], char, font, x, slope_y, rng, settings)
            x += char_width + settings.char_spacing + rng.uniform(-1.2, 0.8)
        new_line(settings.paragraph_spacing)

    rendered = [page.convert("RGB") for page in pages]
    direct_photo_template = (
        scene_background_path is None
        and (
            (background_path is None and settings.paper_style in PAPER_TEMPLATE_CONFIG)
            or (background_path is not None and settings.direct_background)
        )
    )
    if settings.scene_mode == "desk_photo" and not direct_photo_template:
        return [compose_desk_photo(page, settings, index, scene_background_path) for index, page in enumerate(rendered)]
    return rendered


def save_outputs(pages: list[Image.Image], output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    Image.init()
    page_files: list[str] = []
    for index, page in enumerate(pages, start=1):
        filename = f"page-{index:03d}.png"
        path = output_dir / filename
        page.save(path)
        page_files.append(filename)

    pdf_name = "handdraft.pdf"
    pdf_path = output_dir / pdf_name
    first, rest = pages[0], pages[1:]
    first.save(pdf_path, save_all=True, append_images=rest, resolution=150.0)

    zip_name = "handdraft-pages.zip"
    zip_path = output_dir / zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename in page_files:
            archive.write(output_dir / filename, arcname=filename)
        archive.write(pdf_path, arcname=pdf_name)

    return {"page_files": page_files, "pdf": pdf_name, "zip": zip_name}
