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
FRAME_TIMES = [0, 6, 10, 16, 22, 26, 32]
KEY_TIMES = ";".join(f"{point / CYCLE:.6f}".rstrip("0").rstrip(".") for point in FRAME_TIMES)
PIXEL_SCALE = 7
SPRITE_WIDTH = 26
SPRITE_HEIGHT = 17

Cell = tuple[int, int]


@dataclass(frozen=True)
class ScenePalette:
    background_start: str
    background_end: str
    glow: str
    glow_secondary: str
    platform: str
    platform_shadow: str
    frame: str
    frame_soft: str
    yarn_fill: str
    yarn_line: str


@dataclass(frozen=True)
class FurPalette:
    outline: str
    fill: str
    shadow: str
    ear: str
    nose: str


@dataclass(frozen=True)
class Variant:
    flip: int
    cat_x: int
    cat_y: int
    platform_width: int
    frame_width: int
    frame_height: int
    frame_shift: int
    glow_x: int
    glow_y: int
    ball_offset: int
    fur_index: int
    accent_index: int


LIGHT_SCENES = [
    ScenePalette("#f8f1e6", "#dfe8f2", "#f1d8c8", "#d7e7eb", "#73818d", "#b3c1ca", "#5d7080", "#96a7b3", "#d8a36e", "#8e5c42"),
    ScenePalette("#faf4ec", "#e0eaf6", "#efdbcb", "#d8e7df", "#74848f", "#b1bec7", "#5b6f79", "#95a8b0", "#cf9b72", "#905d47"),
    ScenePalette("#f7f1e9", "#dbe8ee", "#ebdacc", "#dae7ee", "#687983", "#aab8c1", "#5d6f79", "#94a7af", "#d2a06a", "#8b593f"),
]

DARK_SCENES = [
    ScenePalette("#121a25", "#202c38", "#21374a", "#173039", "#7d909d", "#425563", "#8ca1b1", "#4d6272", "#dd9d5c", "#f1cfa6"),
    ScenePalette("#101925", "#1b2735", "#29384d", "#16313a", "#8095a3", "#465867", "#90a4b0", "#516372", "#dba36a", "#f0d6ad"),
    ScenePalette("#0f1922", "#1d2832", "#24394a", "#18343d", "#81949e", "#465b65", "#91a2aa", "#536872", "#d8a169", "#f3d4aa"),
]

FUR_PALETTES = [
    FurPalette("#3c2a22", "#d69754", "#b86f39", "#efc29d", "#7d5060"),
    FurPalette("#2f343b", "#9ba3ad", "#6f7781", "#d7c3b9", "#e39a8c"),
    FurPalette("#43352b", "#ead8b7", "#cbb289", "#f2dcc2", "#ad6f71"),
    FurPalette("#2b2b2b", "#f2f2ec", "#a5a5a0", "#f0d3c2", "#d88d85"),
]


def slot_time(moment: datetime) -> datetime:
    return moment.replace(hour=(moment.hour // 4) * 4, minute=0, second=0, microsecond=0)


def build_seed(moment: datetime) -> int:
    return int(sha256(moment.strftime("%Y-%m-%d-%H").encode("utf-8")).hexdigest()[:16], 16)


def choose_scene(theme: str, moment: datetime) -> ScenePalette:
    slot = (moment.timetuple().tm_yday + moment.hour // 4) % 3
    return (DARK_SCENES if theme == "dark" else LIGHT_SCENES)[slot]


def choose_variant(moment: datetime) -> Variant:
    rng = random.Random(build_seed(moment))
    return Variant(
        flip=-1 if rng.random() < 0.5 else 1,
        cat_x=388 + rng.randrange(-16, 17, 8),
        cat_y=168 + rng.randrange(-8, 9, 8),
        platform_width=248 + rng.randrange(-24, 25, 8),
        frame_width=188 + rng.randrange(-16, 17, 8),
        frame_height=116 + rng.randrange(-16, 17, 8),
        frame_shift=rng.randrange(-16, 17, 8),
        glow_x=rng.randrange(-48, 49, 8),
        glow_y=rng.randrange(-24, 25, 8),
        ball_offset=rng.randrange(-8, 17, 8),
        fur_index=rng.randrange(len(FUR_PALETTES)),
        accent_index=rng.randrange(2),
    )


def fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    return f"{value:.3f}".rstrip("0").rstrip(".")


def add_rect(cells: set[Cell], x: int, y: int, width: int, height: int) -> None:
    for iy in range(y, y + height):
        for ix in range(x, x + width):
            cells.add((ix, iy))


def shift_cells(cells: set[Cell], dx: int = 0, dy: int = 0) -> set[Cell]:
    return {(x + dx, y + dy) for x, y in cells}


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
    return "\n      ".join(rects)


def animated_opacity(frame_index: int) -> str:
    values = ["0"] * 6
    values[frame_index] = "1"
    values.append(values[0])
    return ";".join(values)


def animated_ball_translate(variant: Variant) -> str:
    values = [
        (0, 0),
        (0, 0),
        (0, 0),
        (2, -1),
        (5, -4),
        (1, 0),
        (0, 0),
    ]
    return ";".join(f"{x} {y}" for x, y in values)


def animated_ball_rotate() -> str:
    values = [0, 0, 0, 90, 260, 320, 360]
    return ";".join(f"{value} 0 0" for value in values)


def cat_body(loaf: bool = True, stretch: int = 0, rise: int = 0) -> tuple[set[Cell], set[Cell]]:
    fur: set[Cell] = set()
    shadow: set[Cell] = set()

    if loaf:
        add_rect(fur, 6, 6 + rise, 5 + stretch, 1)
        add_rect(fur, 4, 7 + rise, 10 + stretch, 1)
        add_rect(fur, 3, 8 + rise, 13 + stretch, 3)
        add_rect(fur, 4, 11 + rise, 11 + stretch, 1)
        add_rect(fur, 6, 12 + rise, 7 + stretch, 1)
        add_rect(shadow, 6, 9 + rise, 7 + stretch, 1)
        add_rect(shadow, 7, 10 + rise, 5 + stretch, 1)
    else:
        add_rect(fur, 6, 5 + rise, 6, 1)
        add_rect(fur, 5, 6 + rise, 9, 1)
        add_rect(fur, 4, 7 + rise, 10, 3)
        add_rect(fur, 5, 10 + rise, 8, 1)
        add_rect(shadow, 6, 8 + rise, 5, 1)
        add_rect(shadow, 7, 9 + rise, 4, 1)

    return fur, shadow


def cat_head(head_x: int, head_y: int) -> tuple[set[Cell], set[Cell], set[Cell]]:
    fur: set[Cell] = set()
    shadow: set[Cell] = set()
    ear: set[Cell] = set()

    add_rect(fur, head_x + 1, head_y, 4, 1)
    add_rect(fur, head_x, head_y + 1, 6, 4)
    add_rect(fur, head_x + 1, head_y + 5, 4, 1)
    add_rect(shadow, head_x + 1, head_y + 4, 3, 1)
    add_rect(ear, head_x + 1, head_y - 1, 2, 1)
    add_rect(ear, head_x + 4, head_y - 1, 2, 1)
    add_rect(ear, head_x + 2, head_y - 2, 1, 1)
    add_rect(ear, head_x + 5, head_y - 2, 1, 1)

    return fur, shadow, ear


def cat_tail(mode: str) -> set[Cell]:
    cells: set[Cell] = set()
    if mode == "curl":
        add_rect(cells, 2, 8, 1, 2)
        add_rect(cells, 1, 9, 1, 2)
        add_rect(cells, 0, 10, 1, 1)
        add_rect(cells, 1, 11, 2, 1)
        add_rect(cells, 2, 7, 1, 1)
    elif mode == "lift":
        add_rect(cells, 3, 5, 1, 4)
        add_rect(cells, 2, 4, 1, 3)
        add_rect(cells, 1, 4, 1, 1)
        add_rect(cells, 4, 7, 1, 2)
    else:
        add_rect(cells, 1, 8, 1, 2)
        add_rect(cells, 0, 9, 1, 1)
        add_rect(cells, 2, 9, 1, 2)
        add_rect(cells, 3, 10, 1, 1)
    return cells


def paws(mode: str, rise: int = 0) -> set[Cell]:
    cells: set[Cell] = set()
    if mode == "tucked":
        add_rect(cells, 10, 12 + rise, 2, 2)
        add_rect(cells, 13, 12 + rise, 2, 2)
    elif mode == "groom":
        add_rect(cells, 11, 12 + rise, 2, 2)
        add_rect(cells, 15, 8 + rise, 2, 4)
    elif mode == "play":
        add_rect(cells, 10, 12 + rise, 2, 2)
        add_rect(cells, 14, 11 + rise, 4, 1)
        add_rect(cells, 17, 10 + rise, 1, 2)
    elif mode == "jump":
        add_rect(cells, 6, 11 + rise, 2, 3)
        add_rect(cells, 10, 11 + rise, 2, 3)
        add_rect(cells, 13, 11 + rise, 2, 3)
    return cells


def face(mode: str, head_x: int, head_y: int) -> tuple[set[Cell], set[Cell], set[Cell]]:
    dark: set[Cell] = set()
    nose: set[Cell] = set()
    whisker: set[Cell] = set()

    add_rect(whisker, head_x + 6, head_y + 2, 2, 1)
    add_rect(whisker, head_x + 6, head_y + 3, 3, 1)
    add_rect(whisker, head_x + 6, head_y + 4, 2, 1)
    add_rect(nose, head_x + 5, head_y + 3, 1, 1)

    if mode == "sleep":
        add_rect(dark, head_x + 2, head_y + 2, 2, 1)
        add_rect(dark, head_x + 5, head_y + 3, 1, 1)
        add_rect(dark, head_x + 4, head_y + 4, 1, 1)
    elif mode == "yawn":
        add_rect(dark, head_x + 2, head_y + 2, 1, 2)
        add_rect(dark, head_x + 4, head_y + 3, 1, 1)
        add_rect(nose, head_x + 5, head_y + 4, 2, 2)
    elif mode == "groom":
        add_rect(dark, head_x + 2, head_y + 2, 1, 2)
        add_rect(dark, head_x + 4, head_y + 3, 1, 1)
        add_rect(nose, head_x + 5, head_y + 4, 1, 2)
    elif mode == "play":
        add_rect(dark, head_x + 2, head_y + 2, 1, 2)
        add_rect(dark, head_x + 4, head_y + 2, 1, 1)
        add_rect(dark, head_x + 5, head_y + 3, 1, 1)
    elif mode == "jump":
        add_rect(dark, head_x + 2, head_y + 2, 1, 2)
        add_rect(dark, head_x + 4, head_y + 2, 1, 2)
        add_rect(nose, head_x + 5, head_y + 4, 1, 1)
    elif mode == "settle":
        add_rect(dark, head_x + 2, head_y + 2, 1, 2)
        add_rect(dark, head_x + 4, head_y + 3, 1, 1)
        add_rect(nose, head_x + 5, head_y + 4, 1, 1)

    return dark, nose, whisker


def build_frame(mode: str) -> dict[str, set[Cell]]:
    layers = {
        "fur": set(),
        "shadow": set(),
        "ear": set(),
        "face": set(),
        "nose": set(),
        "whisker": set(),
    }

    if mode == "jump":
        body_fur, body_shadow = cat_body(loaf=False, rise=-1)
        head_x, head_y = 12, 2
        paw_cells = paws("jump", rise=-1)
        tail_cells = cat_tail("lift")
        face_dark, nose_cells, whiskers = face("jump", head_x, head_y)
    elif mode == "play":
        body_fur, body_shadow = cat_body(loaf=True, stretch=1)
        head_x, head_y = 13, 4
        paw_cells = paws("play")
        tail_cells = cat_tail("rest")
        face_dark, nose_cells, whiskers = face("play", head_x, head_y)
    elif mode == "groom":
        body_fur, body_shadow = cat_body(loaf=True)
        head_x, head_y = 13, 3
        paw_cells = paws("groom")
        tail_cells = cat_tail("curl")
        face_dark, nose_cells, whiskers = face("groom", head_x, head_y)
    elif mode == "yawn":
        body_fur, body_shadow = cat_body(loaf=True)
        head_x, head_y = 13, 3
        paw_cells = paws("tucked")
        tail_cells = cat_tail("curl")
        face_dark, nose_cells, whiskers = face("yawn", head_x, head_y)
    elif mode == "settle":
        body_fur, body_shadow = cat_body(loaf=True)
        head_x, head_y = 13, 4
        paw_cells = paws("tucked")
        tail_cells = cat_tail("curl")
        face_dark, nose_cells, whiskers = face("settle", head_x, head_y)
    else:
        body_fur, body_shadow = cat_body(loaf=True)
        head_x, head_y = 13, 4
        paw_cells = paws("tucked")
        tail_cells = cat_tail("curl")
        face_dark, nose_cells, whiskers = face("sleep", head_x, head_y)

    head_fur, head_shadow, ear_cells = cat_head(head_x, head_y)

    layers["fur"].update(body_fur | head_fur | paw_cells | tail_cells)
    layers["shadow"].update(body_shadow | head_shadow)
    layers["ear"].update(ear_cells)
    layers["face"].update(face_dark)
    layers["nose"].update(nose_cells)
    layers["whisker"].update(whiskers)
    return layers


def render_frame(mode: str, fur: FurPalette) -> str:
    layers = build_frame(mode)
    body_cells = layers["fur"] | layers["shadow"] | layers["ear"]
    outline = outline_cells(body_cells)

    return f"""
      <g opacity="0">
        <animate attributeName="opacity" values="{animated_opacity(['sleep', 'yawn', 'groom', 'play', 'jump', 'settle'].index(mode))}"
                 keyTimes="{KEY_TIMES}" dur="{CYCLE}s" repeatCount="indefinite" />
        {render_cells(outline, fur.outline)}
        {render_cells(layers["fur"], fur.fill)}
        {render_cells(layers["shadow"], fur.shadow)}
        {render_cells(layers["ear"], fur.ear)}
        {render_cells(layers["face"], fur.outline)}
        {render_cells(layers["nose"], fur.nose)}
        {render_cells(layers["whisker"], fur.outline)}
      </g>"""


def render_stage(scene: ScenePalette, variant: Variant) -> str:
    center_x = variant.cat_x + SPRITE_WIDTH * PIXEL_SCALE / 2
    frame_left = center_x - variant.frame_width / 2
    frame_right = center_x + variant.frame_width / 2
    frame_top = variant.cat_y - variant.frame_height / 2 + variant.frame_shift
    frame_bottom = variant.cat_y + 138
    platform_left = center_x - variant.platform_width / 2
    platform_width = variant.platform_width

    return f"""
  <g>
    <ellipse cx="{fmt(center_x + variant.glow_x)}" cy="{fmt(188 + variant.glow_y)}" rx="188" ry="122" fill="{scene.glow}" opacity="0.28" />
    <ellipse cx="{fmt(center_x - variant.glow_x / 2)}" cy="{fmt(220 - variant.glow_y / 2)}" rx="120" ry="84" fill="{scene.glow_secondary}" opacity="0.18" />
  </g>

  <g shape-rendering="crispEdges">
    <rect x="{fmt(frame_left + 16)}" y="{fmt(frame_top)}" width="{fmt(frame_right - frame_left - 32)}" height="8" fill="{scene.frame_soft}" opacity="0.28" />
    <rect x="{fmt(frame_left)}" y="{fmt(frame_top + 8)}" width="8" height="{fmt(frame_bottom - frame_top - 16)}" fill="{scene.frame_soft}" opacity="0.28" />
    <rect x="{fmt(frame_right - 8)}" y="{fmt(frame_top + 8)}" width="8" height="{fmt(frame_bottom - frame_top - 16)}" fill="{scene.frame_soft}" opacity="0.28" />
    <rect x="{fmt(frame_left + 32)}" y="{fmt(frame_top + 32)}" width="{fmt(frame_right - frame_left - 64)}" height="8" fill="{scene.frame}" opacity="0.18" />

    <rect x="{fmt(platform_left - 32)}" y="312" width="{fmt(platform_width + 64)}" height="8" fill="{scene.platform}" opacity="0.88" />
    <rect x="{fmt(platform_left - 16)}" y="320" width="{fmt(platform_width + 32)}" height="8" fill="{scene.platform}" opacity="0.64" />
    <rect x="{fmt(platform_left + 16)}" y="328" width="{fmt(platform_width - 32)}" height="8" fill="{scene.platform_shadow}" opacity="0.46" />
  </g>"""


def render_yarn(scene: ScenePalette, fur: FurPalette, variant: Variant) -> str:
    ball_x = 22 + variant.ball_offset // 8
    ball_y = 11
    ball_cells: set[Cell] = set()
    add_rect(ball_cells, ball_x, ball_y, 3, 3)
    add_rect(ball_cells, ball_x + 1, ball_y - 1, 1, 1)
    add_rect(ball_cells, ball_x + 3, ball_y + 1, 1, 1)
    ball_outline = outline_cells(ball_cells)

    string_cells: set[Cell] = set()
    add_rect(string_cells, ball_x - 3, ball_y + 1, 3, 1)

    return f"""
      <g transform="translate(0 0)">
        <animateTransform attributeName="transform" type="translate" values="{animated_ball_translate(variant)}"
                          keyTimes="{KEY_TIMES}" dur="{CYCLE}s" repeatCount="indefinite" />
        <g>
          <animateTransform attributeName="transform" type="rotate" values="{animated_ball_rotate()}"
                            keyTimes="{KEY_TIMES}" dur="{CYCLE}s" repeatCount="indefinite" />
          {render_cells(ball_outline | string_cells, scene.yarn_line)}
          {render_cells(ball_cells, scene.yarn_fill)}
          <rect x="{ball_x + 1}" y="{ball_y + 1}" width="1" height="1" fill="{fur.nose}" />
        </g>
      </g>"""


def render_cat(scene: ScenePalette, fur: FurPalette, variant: Variant) -> str:
    flip_group = ""
    if variant.flip == -1:
        flip_group = f'transform="translate({SPRITE_WIDTH} 0) scale(-1 1)"'

    frames = "\n".join(
        render_frame(mode, fur) for mode in ("sleep", "yawn", "groom", "play", "jump", "settle")
    )

    return f"""
  <g transform="translate({variant.cat_x} {variant.cat_y}) scale({PIXEL_SCALE} {PIXEL_SCALE})"
     shape-rendering="crispEdges">
    <g {flip_group}>
{frames}
{render_yarn(scene, fur, variant)}
    </g>
  </g>"""


def render_svg(theme: str, moment: datetime) -> str:
    scene = choose_scene(theme, moment)
    variant = choose_variant(moment)
    fur = FUR_PALETTES[variant.fur_index]

    return f"""<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">Animated pixel-art cat on a quiet stage</title>
  <desc id="desc">A pixel-art cat sleeps, yawns, grooms, bats a yarn ball, makes a small hop, and settles back down.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="{WIDTH}" y2="{HEIGHT}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{scene.background_start}" />
      <stop offset="100%" stop-color="{scene.background_end}" />
    </linearGradient>
  </defs>

  <rect width="{WIDTH}" height="{HEIGHT}" rx="28" fill="url(#bg)" />
{render_stage(scene, variant)}
{render_cat(scene, fur, variant)}
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
