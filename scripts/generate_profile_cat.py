#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import random

WIDTH = 960
HEIGHT = 420
CYCLE = 32
FRAME_ORDER = ("idle", "blink", "meow", "play", "hop", "sleep")
FRAME_TIMES = [0, 6, 10, 16, 22, 26, 32]
KEY_TIMES = ";".join(f"{point / CYCLE:.6f}".rstrip("0").rstrip(".") for point in FRAME_TIMES)
SPRITE_WIDTH = 20
SPRITE_HEIGHT = 18
SPRITE_SCALE = 10

Cell = tuple[int, int]


@dataclass(frozen=True)
class ScenePalette:
    background_start: str
    background_end: str
    glow: str
    shadow: str
    shadow_soft: str
    floor: str
    bubble_fill: str
    bubble_text: str


@dataclass(frozen=True)
class FurPalette:
    outline: str
    fill: str
    shadow: str
    ear: str
    blush: str
    nose: str


@dataclass(frozen=True)
class Variant:
    cat_x: int
    cat_y: int
    glow_dx: int
    glow_dy: int
    ball_dx: int
    fur_index: int
    scene_index: int


LIGHT_SCENES = [
    ScenePalette("#f4f3f2", "#dedfe6", "#ebe7e1", "#c7ccd4", "#d5d9df", "#aeb4be", "#fcfcfc", "#111111"),
    ScenePalette("#f2f1ef", "#dbe1e8", "#ebe2da", "#c8ccd3", "#d8dce1", "#adb2bc", "#fbfbfb", "#101010"),
    ScenePalette("#f1efec", "#dde2e7", "#e7e1db", "#c7ccd1", "#d3d9de", "#b0b5bd", "#fbfbfb", "#111111"),
]

DARK_SCENES = [
    ScenePalette("#1a2430", "#242f3d", "#2c3948", "#0e141b", "#18202a", "#5f6873", "#f0f1f3", "#111111"),
    ScenePalette("#18222d", "#24303a", "#2b3844", "#10161d", "#172029", "#5d6771", "#eeeff2", "#111111"),
    ScenePalette("#19212b", "#252d39", "#303b46", "#0f151d", "#18212a", "#606973", "#f1f2f4", "#111111"),
]

FUR_PALETTES = [
    FurPalette("#111111", "#9e9e9e", "#6d6d6d", "#676767", "#e8a6bd", "#111111"),
    FurPalette("#111111", "#d9c49b", "#b3956d", "#caa780", "#e8a6bd", "#111111"),
    FurPalette("#111111", "#d48d66", "#b76b46", "#d9a37e", "#e8a6bd", "#111111"),
    FurPalette("#111111", "#cfcfd1", "#9b9ba0", "#b8b8bb", "#e8a6bd", "#111111"),
]

BODY_ART = (
    ".......A....A.......",
    "......ACA..ACA......",
    ".....AAAAAAAAAA.....",
    "....AAAAAAAAAAAA....",
    "....AAAAAAAAAAAA....",
    "....AAAAAAAAAAAA....",
    "....AAAAAAAAAAAA....",
    "....AAAAAAAAAAAA....",
    "...AAAAAAAAAAAAAA...",
    "...AAASAAAAASAAAA...",
    "...AAAAAAAAAAAAAA...",
    "...AAAAAAAAAAAAAAT..",
    "...AAAAAAAAAAAAAATT.",
    "...AAAAAAAAAAAAAATT.",
    "....AAAAA..AAAAATT..",
    "....AAAAA..AAAAATT..",
    ".....AAA....AAATT...",
    ".............TT.....",
)

GLYPHS = {
    "M": ("10001", "11011", "10101", "10001", "10001"),
    "E": ("11111", "10000", "11110", "10000", "11111"),
    "O": ("01110", "10001", "10001", "10001", "01110"),
    "W": ("10001", "10001", "10101", "11011", "10001"),
    "!": ("1", "1", "1", "0", "1"),
    "Z": ("11111", "00010", "00100", "01000", "11111"),
    ".": ("0", "0", "0", "0", "1"),
    " ": ("0", "0", "0", "0", "0"),
}

BUBBLE_TEXT = {
    "idle": "...",
    "blink": "...",
    "meow": "MEOW!",
    "play": "MEOW!",
    "hop": "!",
    "sleep": "ZZZ",
}

CAT_TRANSLATE_VALUES = "0 0;0 0;0 -4;0 -2;0 -20;0 -2;0 0"
BUBBLE_TRANSLATE_VALUES = "0 0;0 0;0 -2;0 -1;0 -8;0 -1;0 0"
BALL_TRANSLATE_VALUES = "0 0;0 0;0 0;8 -4;4 -2;0 0;0 0"
BALL_ROTATE_VALUES = "0 0 0;0 0 0;0 0 0;120 0 0;240 0 0;360 0 0;360 0 0"


def slot_time(moment: datetime) -> datetime:
    return moment.replace(hour=(moment.hour // 4) * 4, minute=0, second=0, microsecond=0)


def build_seed(moment: datetime) -> int:
    return int(sha256(moment.strftime("%Y-%m-%d-%H").encode("utf-8")).hexdigest()[:16], 16)


def choose_variant(moment: datetime) -> Variant:
    rng = random.Random(build_seed(moment))
    return Variant(
        cat_x=378 + rng.randrange(-16, 17, 8),
        cat_y=146 + rng.randrange(-8, 9, 8),
        glow_dx=rng.randrange(-40, 41, 8),
        glow_dy=rng.randrange(-24, 25, 8),
        ball_dx=rng.randrange(-8, 17, 8),
        fur_index=rng.randrange(len(FUR_PALETTES)),
        scene_index=rng.randrange(3),
    )


def fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def add_rect(cells: set[Cell], x: int, y: int, width: int, height: int) -> None:
    for iy in range(y, y + height):
        for ix in range(x, x + width):
            cells.add((ix, iy))


def outline_cells(cells: set[Cell]) -> set[Cell]:
    outline: set[Cell] = set()
    for x, y in cells:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor = (x + dx, y + dy)
                if neighbor not in cells:
                    outline.add(neighbor)
    outline.difference_update(cells)
    return outline


def render_cells(cells: set[Cell], color: str) -> str:
    if not cells:
        return ""

    rows: dict[int, list[int]] = {}
    for x, y in cells:
        rows.setdefault(y, []).append(x)

    rects: list[str] = []
    for y in sorted(rows):
        xs = sorted(rows[y])
        start = xs[0]
        prev = xs[0]
        for x in xs[1:]:
            if x == prev + 1:
                prev = x
                continue
            rects.append(
                f'<rect x="{start}" y="{y}" width="{prev - start + 1}" height="1" fill="{color}" />'
            )
            start = prev = x
        rects.append(
            f'<rect x="{start}" y="{y}" width="{prev - start + 1}" height="1" fill="{color}" />'
        )
    return "\n        ".join(rects)


def frame_opacity(mode: str) -> str:
    values = ["0"] * len(FRAME_ORDER)
    values[FRAME_ORDER.index(mode)] = "1"
    values.append(values[0])
    return ";".join(values)


def parse_body_art() -> dict[str, set[Cell]]:
    layers = {
        "base": set(),
        "shadow": set(),
        "ear": set(),
        "stripe": set(),
    }

    for y, row in enumerate(BODY_ART):
        if len(row) != SPRITE_WIDTH:
            raise ValueError(f"body art row has width {len(row)}, expected {SPRITE_WIDTH}")
        for x, char in enumerate(row):
            if char == ".":
                continue
            layers["base"].add((x, y))
            if char == "S":
                layers["shadow"].add((x, y))
            elif char == "C":
                layers["ear"].add((x, y))
            elif char == "T":
                layers["stripe"].add((x, y))
    return layers


BODY_LAYERS = parse_body_art()
BODY_OUTLINE = outline_cells(BODY_LAYERS["base"])


def face_features(mode: str) -> dict[str, set[Cell]]:
    face: set[Cell] = set()
    nose: set[Cell] = {(9, 7)}
    blush: set[Cell] = {(6, 7), (13, 7)}

    if mode == "idle":
        face.update({(8, 5), (11, 5), (8, 8), (11, 8), (9, 9), (10, 9)})
    elif mode == "blink":
        face.update({(7, 5), (8, 5), (11, 5), (12, 5), (8, 8), (11, 8)})
    elif mode == "meow":
        face.update({(8, 5), (11, 5), (9, 8), (10, 8), (9, 9), (10, 9)})
        nose = {(9, 7), (10, 7)}
        blush.update({(5, 7), (14, 7)})
    elif mode == "play":
        face.update({(7, 5), (8, 5), (11, 5), (8, 8), (9, 8), (11, 8)})
        blush.update({(5, 7), (14, 7)})
    elif mode == "hop":
        face.update({(8, 5), (11, 5), (7, 6), (12, 6), (9, 8), (10, 8)})
        nose = {(9, 7), (10, 7)}
        blush.update({(5, 7), (14, 7)})
    elif mode == "sleep":
        face.update({(7, 5), (8, 5), (11, 5), (12, 5), (9, 8), (10, 8)})
        blush = {(6, 7), (13, 7)}

    return {"face": face, "nose": nose, "blush": blush}


def render_cat_frame(mode: str, fur: FurPalette) -> str:
    features = face_features(mode)
    return f"""
      <g opacity="0">
        <animate attributeName="opacity" values="{frame_opacity(mode)}"
                 keyTimes="{KEY_TIMES}" dur="{CYCLE}s" repeatCount="indefinite" />
        {render_cells(BODY_OUTLINE, fur.outline)}
        {render_cells(BODY_LAYERS["base"], fur.fill)}
        {render_cells(BODY_LAYERS["shadow"], fur.shadow)}
        {render_cells(BODY_LAYERS["ear"], fur.ear)}
        {render_cells(BODY_LAYERS["stripe"], fur.shadow)}
        {render_cells(features["blush"], fur.blush)}
        {render_cells(features["face"], fur.outline)}
        {render_cells(features["nose"], fur.nose)}
      </g>"""


def glyph_cells(text: str) -> tuple[set[Cell], int]:
    cells: set[Cell] = set()
    cursor = 0

    for index, char in enumerate(text):
        glyph = GLYPHS[char]
        width = len(glyph[0])
        for y, row in enumerate(glyph):
            for x, pixel in enumerate(row):
                if pixel == "1":
                    cells.add((cursor + x, y))
        cursor += width
        if index != len(text) - 1:
            cursor += 1

    return cells, cursor


def bubble_shell_cells() -> tuple[set[Cell], set[Cell]]:
    outline: set[Cell] = set()
    fill: set[Cell] = set()
    width = 32
    height = 11

    add_rect(fill, 2, 1, width - 4, height - 2)
    add_rect(fill, 1, 2, width - 2, height - 4)

    for x in range(2, width - 2):
        outline.add((x, 0))
        outline.add((x, height - 1))
    for y in range(2, height - 2):
        outline.add((0, y))
        outline.add((width - 1, y))
    outline.update(
        {
            (1, 1),
            (width - 2, 1),
            (1, height - 2),
            (width - 2, height - 2),
            (9, height - 1),
            (10, height),
            (11, height + 1),
            (12, height + 2),
            (12, height + 1),
            (11, height),
        }
    )
    fill.update({(10, height - 1), (11, height), (11, height + 1)})
    return outline, fill


BUBBLE_OUTLINE, BUBBLE_FILL = bubble_shell_cells()


def render_bubble(scene: ScenePalette, variant: Variant) -> str:
    bubble_x = variant.cat_x + 28
    bubble_y = 42
    groups: list[str] = []

    for mode in FRAME_ORDER:
        text_cells, text_width = glyph_cells(BUBBLE_TEXT[mode])
        offset_x = max(0, (32 - text_width) // 2)
        shifted_text = {(x + offset_x, y + 3) for x, y in text_cells}
        groups.append(
            f"""
      <g opacity="0">
        <animate attributeName="opacity" values="{frame_opacity(mode)}"
                 keyTimes="{KEY_TIMES}" dur="{CYCLE}s" repeatCount="indefinite" />
        {render_cells(shifted_text, scene.bubble_text)}
      </g>"""
        )

    return f"""
  <g transform="translate({bubble_x} {bubble_y}) scale(4 4)" shape-rendering="crispEdges">
    <animateTransform attributeName="transform" type="translate" values="{BUBBLE_TRANSLATE_VALUES}"
                      keyTimes="{KEY_TIMES}" dur="{CYCLE}s" repeatCount="indefinite" additive="sum" />
    {render_cells(BUBBLE_FILL, scene.bubble_fill)}
    {render_cells(BUBBLE_OUTLINE, "#111111")}
{''.join(groups)}
  </g>"""


def render_yarn(scene: ScenePalette, fur: FurPalette, variant: Variant) -> str:
    outline: set[Cell] = set()
    fill: set[Cell] = set()
    string: set[Cell] = set()

    add_rect(fill, 0, 0, 3, 3)
    add_rect(fill, 1, -1, 1, 1)
    add_rect(fill, 3, 1, 1, 1)
    outline.update(outline_cells(fill))
    add_rect(string, -4, 1, 4, 1)

    x = variant.cat_x + 168 + variant.ball_dx
    y = variant.cat_y + 114

    return f"""
  <g transform="translate({x} {y}) scale(6 6)" shape-rendering="crispEdges">
    <animateTransform attributeName="transform" type="translate" values="{BALL_TRANSLATE_VALUES}"
                      keyTimes="{KEY_TIMES}" dur="{CYCLE}s" repeatCount="indefinite" additive="sum" />
    <g>
      <animateTransform attributeName="transform" type="rotate" values="{BALL_ROTATE_VALUES}"
                        keyTimes="{KEY_TIMES}" dur="{CYCLE}s" repeatCount="indefinite" />
      {render_cells(outline | string, "#111111")}
      {render_cells(fill, scene.floor)}
      <rect x="1" y="1" width="1" height="1" fill="{fur.blush}" />
    </g>
  </g>"""


def render_stage(scene: ScenePalette, variant: Variant) -> str:
    center_x = variant.cat_x + SPRITE_WIDTH * SPRITE_SCALE / 2
    center_y = variant.cat_y + SPRITE_HEIGHT * SPRITE_SCALE / 2
    return f"""
  <g>
    <ellipse cx="{fmt(center_x + variant.glow_dx)}" cy="{fmt(center_y - 26 + variant.glow_dy)}" rx="172" ry="132"
             fill="{scene.glow}" opacity="0.34" />
    <ellipse cx="{fmt(center_x)}" cy="332" rx="176" ry="26" fill="{scene.shadow}" opacity="0.72" />
    <ellipse cx="{fmt(center_x)}" cy="324" rx="134" ry="18" fill="{scene.shadow_soft}" opacity="0.86" />
    <rect x="{fmt(center_x - 184)}" y="314" width="368" height="6" fill="{scene.floor}" opacity="0.56" />
  </g>"""


def render_cat(fur: FurPalette, variant: Variant) -> str:
    frames = "\n".join(render_cat_frame(mode, fur) for mode in FRAME_ORDER)
    return f"""
  <g transform="translate({variant.cat_x} {variant.cat_y}) scale({SPRITE_SCALE} {SPRITE_SCALE})"
     shape-rendering="crispEdges">
    <animateTransform attributeName="transform" type="translate" values="{CAT_TRANSLATE_VALUES}"
                      keyTimes="{KEY_TIMES}" dur="{CYCLE}s" repeatCount="indefinite" additive="sum" />
{frames}
  </g>"""


def render_svg(theme: str, moment: datetime) -> str:
    variant = choose_variant(moment)
    scene = (DARK_SCENES if theme == "dark" else LIGHT_SCENES)[variant.scene_index]
    fur = FUR_PALETTES[variant.fur_index]

    return f"""<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">Animated pixel mascot cat artwork</title>
  <desc id="desc">A chibi pixel cat with a speech bubble blinks, meows, bounces, and dozes on a soft background.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="{WIDTH}" y2="{HEIGHT}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{scene.background_start}" />
      <stop offset="100%" stop-color="{scene.background_end}" />
    </linearGradient>
  </defs>

  <rect width="{WIDTH}" height="{HEIGHT}" rx="28" fill="url(#bg)" />
{render_stage(scene, variant)}
{render_bubble(scene, variant)}
{render_cat(fur, variant)}
{render_yarn(scene, fur, variant)}
</svg>
"""


def main() -> None:
    output_dir = Path("dist")
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale_svg in output_dir.glob("*.svg"):
        stale_svg.unlink()

    moment = slot_time(datetime.now(timezone.utc))
    outputs = {
        "profile-cat.svg": render_svg("light", moment),
        "profile-cat-dark.svg": render_svg("dark", moment),
    }

    for name, content in outputs.items():
        (output_dir / name).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
