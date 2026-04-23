#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import random
from PIL import Image

WIDTH = 960
HEIGHT = 420
SCALE = 10
GRID_WIDTH = WIDTH // SCALE
GRID_HEIGHT = HEIGHT // SCALE
DIST_DIR = Path("dist")


@dataclass(frozen=True)
class ScenePalette:
    background: str
    halo: str
    cat_shadow: str
    platform_shadow: str
    platform: str
    sparkle: str


@dataclass(frozen=True)
class FurPalette:
    outline: str
    fill: str
    shade: str
    marking: str
    marking_shade: str
    ear: str
    blush: str
    nose: str
    mouth: str
    eye: str
    yarn: str
    yarn_shade: str


@dataclass(frozen=True)
class Variant:
    fur_index: int
    scene_index: int
    cat_dx: int
    yarn_dx: int
    halo_dx: int
    facing: int


@dataclass(frozen=True)
class FrameSpec:
    name: str
    duration_ms: int
    cat_dy: int = 0
    head_dy: int = 0
    body_dy: int = 0
    eyes: str = "open"
    mouth: str = "smile"
    tail: str = "curl"
    paw: str = "rest"
    yarn_dx: int = 0
    yarn_dy: int = 0
    sleep_marks: int = 0


LIGHT_SCENES = [
    ScenePalette("#efede8", "#f7f4ef", "#cdc7bf", "#d6d0c9", "#c1bbb3", "#ffffff"),
    ScenePalette("#ece9e3", "#f5f1ea", "#ccc5bd", "#d4cec6", "#beb8af", "#ffffff"),
    ScenePalette("#f0ece7", "#f7f3ed", "#cec8c0", "#d8d2ca", "#c3bdb5", "#ffffff"),
]

DARK_SCENES = [
    ScenePalette("#18212b", "#273241", "#10161d", "#1f2b39", "#435163", "#dce3ea"),
    ScenePalette("#17202a", "#293543", "#11161d", "#202b37", "#455465", "#dfe5eb"),
    ScenePalette("#19232c", "#2b3640", "#10171e", "#202c38", "#45505e", "#e0e6eb"),
]

FUR_PALETTES = [
    FurPalette(
        "#111111",
        "#666b74",
        "#474b53",
        "#f1f0ec",
        "#d8dae0",
        "#8d6f71",
        "#e7b6c8",
        "#efb6bf",
        "#7e4953",
        "#b0ab53",
        "#5d98d1",
        "#3d6790",
    ),
]

FRAME_SPECS = [
    FrameSpec("idle-1", 420, tail="curl"),
    FrameSpec("idle-2", 320, cat_dy=1, head_dy=1, body_dy=1, tail="sway"),
    FrameSpec("blink", 170, tail="sway", eyes="blink"),
    FrameSpec("idle-3", 320, tail="curl"),
    FrameSpec("yawn-1", 240, head_dy=-1, tail="perk", eyes="soft", mouth="small-open"),
    FrameSpec("yawn-2", 420, head_dy=-2, tail="perk", eyes="soft", mouth="wide-open"),
    FrameSpec("play-1", 240, tail="high", paw="bat", yarn_dx=-2, yarn_dy=-1),
    FrameSpec("play-2", 240, cat_dy=-1, tail="high", paw="bat-2", yarn_dx=3, yarn_dy=-2),
    FrameSpec("jump", 220, cat_dy=-4, head_dy=-1, body_dy=-1, tail="high", eyes="open", mouth="smile", paw="tuck"),
    FrameSpec("land", 230, cat_dy=-1, head_dy=1, body_dy=1, tail="sway", eyes="blink", mouth="smile"),
    FrameSpec("sleep-1", 620, cat_dy=1, head_dy=1, body_dy=1, tail="rest", eyes="sleep", mouth="tiny", sleep_marks=1),
    FrameSpec("sleep-2", 680, cat_dy=2, head_dy=2, body_dy=2, tail="rest", eyes="sleep", mouth="tiny", sleep_marks=2),
]

GLYPHS = {
    "Z": ("111", "001", "010", "100", "111"),
}


def slot_time(moment: datetime) -> datetime:
    return moment.replace(hour=(moment.hour // 4) * 4, minute=0, second=0, microsecond=0)


def build_seed(moment: datetime) -> int:
    return int(sha256(moment.strftime("%Y-%m-%d-%H").encode("utf-8")).hexdigest()[:16], 16)


def choose_variant(moment: datetime) -> Variant:
    rng = random.Random(build_seed(moment))
    return Variant(
        fur_index=0,
        scene_index=rng.randrange(3),
        cat_dx=rng.randrange(-2, 3),
        yarn_dx=rng.randrange(-3, 4),
        halo_dx=rng.randrange(-4, 5),
        facing=1 if rng.random() >= 0.5 else -1,
    )


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def ellipse_cells(cx: int, cy: int, rx: int, ry: int) -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for y in range(cy - ry, cy + ry + 1):
        for x in range(cx - rx, cx + rx + 1):
            dx = x - cx
            dy = y - cy
            if (dx * dx) * (ry * ry) + (dy * dy) * (rx * rx) <= (rx * rx) * (ry * ry):
                cells.add((x, y))
    return cells


def rect_cells(x: int, y: int, width: int, height: int) -> set[tuple[int, int]]:
    return {(ix, iy) for iy in range(y, y + height) for ix in range(x, x + width)}


def triangle_cells(points: list[tuple[int, int]]) -> set[tuple[int, int]]:
    (x1, y1), (x2, y2), (x3, y3) = points
    min_x = min(x1, x2, x3)
    max_x = max(x1, x2, x3)
    min_y = min(y1, y2, y3)
    max_y = max(y1, y2, y3)
    cells: set[tuple[int, int]] = set()

    def sign(px: int, py: int, ax: int, ay: int, bx: int, by: int) -> int:
        return (px - bx) * (ay - by) - (ax - bx) * (py - by)

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            center_x = x * 2 + 1
            center_y = y * 2 + 1
            b1 = sign(center_x, center_y, x1 * 2, y1 * 2, x2 * 2, y2 * 2) < 0
            b2 = sign(center_x, center_y, x2 * 2, y2 * 2, x3 * 2, y3 * 2) < 0
            b3 = sign(center_x, center_y, x3 * 2, y3 * 2, x1 * 2, y1 * 2) < 0
            if b1 == b2 == b3:
                cells.add((x, y))
    return cells


def outline_cells(cells: set[tuple[int, int]]) -> set[tuple[int, int]]:
    outline: set[tuple[int, int]] = set()
    for x, y in cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor = (x + dx, y + dy)
                if neighbor not in cells:
                    outline.add(neighbor)
    outline.difference_update(cells)
    return outline


def mirror_cells(cells: set[tuple[int, int]], facing: int) -> set[tuple[int, int]]:
    if facing == 1:
        return set(cells)
    return {(-x, y) for x, y in cells}


def shift_cells(cells: set[tuple[int, int]], dx: int, dy: int) -> set[tuple[int, int]]:
    return {(x + dx, y + dy) for x, y in cells}


def new_canvas(fill_index: int) -> list[list[int]]:
    return [[fill_index for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]


def paint_cells(canvas: list[list[int]], cells: set[tuple[int, int]], color_index: int) -> None:
    for x, y in cells:
        if 0 <= x < GRID_WIDTH and 0 <= y < GRID_HEIGHT:
            canvas[y][x] = color_index


def paint_ellipse(canvas: list[list[int]], cx: int, cy: int, rx: int, ry: int, color_index: int) -> None:
    paint_cells(canvas, ellipse_cells(cx, cy, rx, ry), color_index)


def draw_glyph(
    canvas: list[list[int]],
    origin_x: int,
    origin_y: int,
    glyph: str,
    color_index: int,
) -> None:
    rows = GLYPHS[glyph]
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char == "1":
                if 0 <= origin_x + x < GRID_WIDTH and 0 <= origin_y + y < GRID_HEIGHT:
                    canvas[origin_y + y][origin_x + x] = color_index


def cat_layers(spec: FrameSpec, variant: Variant) -> dict[str, set[tuple[int, int]]]:
    facing = variant.facing
    head_cy = -5 + spec.head_dy
    body_cy = 4 + spec.body_dy

    fur = ellipse_cells(0, head_cy, 9, 6)
    fur |= ellipse_cells(0, body_cy, 11, 8)
    fur |= rect_cells(-7, 10 + spec.body_dy, 4, 4)
    fur |= rect_cells(3, 10 + spec.body_dy, 4, 4)
    fur |= rect_cells(-9, -7 + spec.head_dy, 2, 3)
    fur |= rect_cells(7, -7 + spec.head_dy, 2, 3)
    fur |= triangle_cells([(-8, -10 + spec.head_dy), (-5, -16 + spec.head_dy), (-2, -10 + spec.head_dy)])
    fur |= triangle_cells([(8, -10 + spec.head_dy), (5, -16 + spec.head_dy), (2, -10 + spec.head_dy)])

    if spec.paw == "bat":
        fur |= rect_cells(7, 7 + spec.body_dy, 4, 2)
    elif spec.paw == "bat-2":
        fur |= rect_cells(8, 6 + spec.body_dy, 4, 2)
    elif spec.paw == "tuck":
        fur -= rect_cells(-7, 11 + spec.body_dy, 4, 3)
        fur -= rect_cells(3, 11 + spec.body_dy, 4, 3)
        fur |= rect_cells(-6, 9 + spec.body_dy, 3, 3)
        fur |= rect_cells(3, 9 + spec.body_dy, 3, 3)

    if spec.tail == "curl":
        tail_blocks = [(12, 9), (13, 8), (14, 7), (14, 5), (13, 3), (12, 2)]
    elif spec.tail == "sway":
        tail_blocks = [(12, 8), (13, 7), (14, 6), (15, 5), (14, 3)]
    elif spec.tail == "perk":
        tail_blocks = [(11, 8), (12, 6), (13, 4), (13, 2), (12, 0)]
    elif spec.tail == "high":
        tail_blocks = [(11, 7), (12, 5), (13, 3), (13, 1), (12, -1)]
    else:
        tail_blocks = [(11, 10), (12, 10), (13, 9), (14, 8), (14, 7)]

    tail: set[tuple[int, int]] = set()
    for block_x, block_y in tail_blocks:
        tail |= rect_cells(block_x, block_y + spec.body_dy, 2, 2)
    fur |= mirror_cells(tail, facing)

    ear = triangle_cells([(-6, -10 + spec.head_dy), (-5, -14 + spec.head_dy), (-3, -10 + spec.head_dy)])
    ear |= triangle_cells([(6, -10 + spec.head_dy), (5, -14 + spec.head_dy), (3, -10 + spec.head_dy)])

    shade = rect_cells(-9, -2 + spec.body_dy, 2, 6)
    shade |= rect_cells(7, -2 + spec.body_dy, 2, 6)
    shade |= rect_cells(-7, 4 + spec.body_dy, 2, 5)
    shade |= rect_cells(5, 4 + spec.body_dy, 2, 5)
    shade |= rect_cells(-7, 11 + spec.body_dy, 2, 3)
    shade |= rect_cells(5, 11 + spec.body_dy, 2, 3)
    shade |= rect_cells(-7, -7 + spec.head_dy, 2, 3)
    shade |= rect_cells(5, -7 + spec.head_dy, 2, 3)
    shade |= mirror_cells(rect_cells(12, 5 + spec.body_dy, 2, 2), facing)

    markings = ellipse_cells(0, 0 + spec.head_dy, 4, 5)
    markings |= rect_cells(-2, -8 + spec.head_dy, 4, 5)
    markings |= ellipse_cells(0, 6 + spec.body_dy, 6, 8)
    markings |= rect_cells(-4, 10 + spec.body_dy, 3, 4)
    markings |= rect_cells(2, 10 + spec.body_dy, 3, 4)
    markings &= fur

    marking_shade = ellipse_cells(0, 9 + spec.body_dy, 4, 4)
    marking_shade |= rect_cells(-2, 2 + spec.body_dy, 4, 3)
    marking_shade &= markings

    blush = {(-6, -4 + spec.head_dy), (-5, -4 + spec.head_dy), (5, -4 + spec.head_dy), (6, -4 + spec.head_dy)}

    nose = {(0, -3 + spec.head_dy)}
    if spec.mouth == "wide-open":
        nose |= {(0, -4 + spec.head_dy)}

    eyes: set[tuple[int, int]] = set()
    pupils: set[tuple[int, int]] = set()
    mouth: set[tuple[int, int]] = set()
    whiskers = {
        (-9, -2 + spec.head_dy),
        (-8, -2 + spec.head_dy),
        (-9, -1 + spec.head_dy),
        (-8, 0 + spec.head_dy),
        (8, -2 + spec.head_dy),
        (9, -2 + spec.head_dy),
        (8, 0 + spec.head_dy),
        (9, -1 + spec.head_dy),
    }

    if spec.eyes == "open":
        eyes |= {(-4, -5 + spec.head_dy), (-4, -4 + spec.head_dy), (4, -5 + spec.head_dy), (4, -4 + spec.head_dy)}
        pupils |= {(-4, -4 + spec.head_dy), (4, -4 + spec.head_dy)}
    elif spec.eyes == "blink":
        pupils |= {(-5, -4 + spec.head_dy), (-4, -4 + spec.head_dy), (4, -4 + spec.head_dy), (5, -4 + spec.head_dy)}
    elif spec.eyes == "soft":
        eyes |= {(-5, -5 + spec.head_dy), (-4, -5 + spec.head_dy), (4, -5 + spec.head_dy), (5, -5 + spec.head_dy)}
        pupils |= {(-4, -5 + spec.head_dy), (4, -5 + spec.head_dy)}
    else:
        pupils |= {(-5, -4 + spec.head_dy), (-4, -4 + spec.head_dy), (4, -4 + spec.head_dy), (5, -4 + spec.head_dy)}

    if spec.mouth == "smile":
        mouth |= {(-1, -2 + spec.head_dy), (0, -1 + spec.head_dy), (1, -2 + spec.head_dy)}
    elif spec.mouth == "small-open":
        mouth |= {(-1, -2 + spec.head_dy), (0, -1 + spec.head_dy), (1, -2 + spec.head_dy), (0, 0 + spec.head_dy)}
    elif spec.mouth == "wide-open":
        mouth |= {(-1, -2 + spec.head_dy), (0, -2 + spec.head_dy), (1, -2 + spec.head_dy), (-1, -1 + spec.head_dy), (1, -1 + spec.head_dy), (0, 0 + spec.head_dy)}
    else:
        mouth |= {(0, -1 + spec.head_dy)}

    silhouette = fur | ear
    outline = outline_cells(silhouette)

    origin_x = 48 + variant.cat_dx
    origin_y = 23 + spec.cat_dy

    return {
        "outline": shift_cells(outline, origin_x, origin_y),
        "fur": shift_cells(fur, origin_x, origin_y),
        "shade": shift_cells(shade & fur, origin_x, origin_y),
        "markings": shift_cells(markings, origin_x, origin_y),
        "marking_shade": shift_cells(marking_shade, origin_x, origin_y),
        "ear": shift_cells(ear & fur, origin_x, origin_y),
        "blush": shift_cells(blush, origin_x, origin_y),
        "nose": shift_cells(nose, origin_x, origin_y),
        "eyes": shift_cells(eyes, origin_x, origin_y),
        "pupils": shift_cells(pupils, origin_x, origin_y),
        "mouth": shift_cells(mouth, origin_x, origin_y),
        "whiskers": shift_cells(whiskers, origin_x, origin_y),
    }


def yarn_layers(spec: FrameSpec, variant: Variant) -> dict[str, set[tuple[int, int]]]:
    base_x = 48 + variant.cat_dx + variant.facing * (19 + variant.yarn_dx) + spec.yarn_dx
    base_y = 31 + spec.yarn_dy
    yarn = ellipse_cells(base_x, base_y, 3, 3)
    yarn |= rect_cells(base_x - 1, base_y - 1, 3, 2)
    outline = outline_cells(yarn)
    accent = {(base_x - 1, base_y), (base_x, base_y - 1), (base_x + 1, base_y + 1), (base_x, base_y + 2)}
    return {"outline": outline, "fill": yarn, "accent": accent & yarn}


def build_theme(scene: ScenePalette, fur: FurPalette) -> tuple[list[str], dict[str, int]]:
    colors = [
        scene.background,
        scene.halo,
        scene.cat_shadow,
        scene.platform_shadow,
        scene.platform,
        scene.sparkle,
        fur.outline,
        fur.fill,
        fur.shade,
        fur.marking,
        fur.marking_shade,
        fur.ear,
        fur.blush,
        fur.nose,
        fur.mouth,
        fur.eye,
        fur.yarn,
        fur.yarn_shade,
    ]
    palette: list[str] = []
    seen: set[str] = set()
    for color in colors:
        if color not in seen:
            palette.append(color)
            seen.add(color)
    return palette, {color: index for index, color in enumerate(palette)}


def render_logical_frame(
    scene: ScenePalette,
    fur: FurPalette,
    variant: Variant,
    spec: FrameSpec,
    color_index: dict[str, int],
) -> list[list[int]]:
    canvas = new_canvas(color_index[scene.background])

    paint_ellipse(canvas, 48 + variant.halo_dx, 18, 20, 12, color_index[scene.halo])
    paint_ellipse(canvas, 48, 35, 22, 4, color_index[scene.platform_shadow])
    paint_ellipse(canvas, 48, 33, 18, 3, color_index[scene.platform])
    paint_ellipse(canvas, 48 + variant.cat_dx, 32 + spec.cat_dy, 12, 2, color_index[scene.cat_shadow])

    yarn = yarn_layers(spec, variant)
    paint_cells(canvas, yarn["outline"], color_index[fur.outline])
    paint_cells(canvas, yarn["fill"], color_index[fur.yarn])
    paint_cells(canvas, yarn["accent"], color_index[fur.yarn_shade])

    cat = cat_layers(spec, variant)
    paint_cells(canvas, cat["outline"], color_index[fur.outline])
    paint_cells(canvas, cat["fur"], color_index[fur.fill])
    paint_cells(canvas, cat["shade"], color_index[fur.shade])
    paint_cells(canvas, cat["markings"], color_index[fur.marking])
    paint_cells(canvas, cat["marking_shade"], color_index[fur.marking_shade])
    paint_cells(canvas, cat["ear"], color_index[fur.ear])
    paint_cells(canvas, cat["blush"], color_index[fur.blush])
    paint_cells(canvas, cat["nose"], color_index[fur.nose])
    paint_cells(canvas, cat["eyes"], color_index[fur.eye])
    paint_cells(canvas, cat["pupils"], color_index[fur.outline])
    paint_cells(canvas, cat["mouth"], color_index[fur.mouth])
    paint_cells(canvas, cat["whiskers"], color_index[fur.marking_shade])

    for offset in range(spec.sleep_marks):
        draw_glyph(canvas, 58 + offset * 4, 6 - offset * 3, "Z", color_index[scene.sparkle])

    return canvas


def image_from_logical_frame(logical_frame: list[list[int]], palette: list[str]) -> Image.Image:
    image = Image.new("RGB", (GRID_WIDTH, GRID_HEIGHT))
    pixels = image.load()
    rgb_palette = [hex_to_rgb(color) for color in palette]
    for y, row in enumerate(logical_frame):
        for x, color_index in enumerate(row):
            pixels[x, y] = rgb_palette[color_index]
    return image.resize((WIDTH, HEIGHT), Image.Resampling.NEAREST)


def write_animated_gif(
    path: Path,
    logical_frames: list[list[list[int]]],
    durations_ms: list[int],
    palette: list[str],
) -> None:
    frames = [image_from_logical_frame(frame, palette) for frame in logical_frames]
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations_ms,
        loop=0,
        disposal=2,
        optimize=False,
    )


def write_sprite_sheet(path: Path, logical_frames: list[list[list[int]]], palette: list[str]) -> None:
    tile_scale = 5
    frame_gap = 8
    crop_x = 28
    crop_y = 4
    crop_width = 40
    crop_height = 36
    tile_width = crop_width * tile_scale
    tile_height = crop_height * tile_scale
    sheet_width = len(logical_frames) * (tile_width + frame_gap) - frame_gap
    sheet = Image.new("RGB", (sheet_width, tile_height), hex_to_rgb(palette[0]))

    for frame_index, frame in enumerate(logical_frames):
        tile = image_from_logical_frame(frame, palette)
        tile = tile.crop((crop_x * SCALE, crop_y * SCALE, (crop_x + crop_width) * SCALE, (crop_y + crop_height) * SCALE))
        tile = tile.resize((tile_width, tile_height), Image.Resampling.NEAREST)
        offset_x = frame_index * (tile_width + frame_gap)
        sheet.paste(tile, (offset_x, 0))

    sheet.save(path)


def generate_assets(theme: str, moment: datetime, output_name: str) -> None:
    variant = choose_variant(moment)
    scene = (DARK_SCENES if theme == "dark" else LIGHT_SCENES)[variant.scene_index]
    fur = FUR_PALETTES[variant.fur_index]
    palette, color_index = build_theme(scene, fur)

    logical_frames = [render_logical_frame(scene, fur, variant, spec, color_index) for spec in FRAME_SPECS]
    durations = [spec.duration_ms for spec in FRAME_SPECS]

    write_animated_gif(DIST_DIR / f"{output_name}.gif", logical_frames, durations, palette)
    write_sprite_sheet(DIST_DIR / f"{output_name}-sheet.png", logical_frames, palette)


def main() -> None:
    DIST_DIR.mkdir(exist_ok=True)
    for path in DIST_DIR.glob("*"):
        if path.is_file():
            path.unlink()

    moment = slot_time(datetime.now(timezone.utc))
    generate_assets("light", moment, "profile-cat")
    generate_assets("dark", moment, "profile-cat-dark")


if __name__ == "__main__":
    main()
