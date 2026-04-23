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
TIMELINE = [0, 6, 10, 16, 22, 24, 26, 32]
KEY_TIMES = ";".join(f"{point / CYCLE:.6f}".rstrip("0").rstrip(".") for point in TIMELINE)


@dataclass(frozen=True)
class Palette:
    background_start: str
    background_end: str
    haze: str
    haze_secondary: str
    stage: str
    stage_soft: str
    line: str
    line_soft: str
    cat_fill: str
    cat_fill_soft: str
    accent_a: str
    accent_b: str
    yarn_fill: str
    yarn_line: str


@dataclass(frozen=True)
class Variant:
    flip: int
    cat_x: float
    cat_y: float
    ball_distance: float
    arch_rx: float
    arch_control_y: float
    arc_drift: float
    glow_x: float
    glow_y: float
    secondary_glow: bool
    accent_index: int
    micro_phase: float


LIGHT_PALETTES = [
    Palette(
        "#f8f4ea",
        "#e3edf4",
        "#efd9c7",
        "#dce8ee",
        "#6e7b87",
        "#a9b8c3",
        "#29333a",
        "#6f818e",
        "#fffaf2",
        "#f2e7da",
        "#d97a57",
        "#4f93a1",
        "#d8a56e",
        "#8b5a42",
    ),
    Palette(
        "#fbf6ed",
        "#e6edf7",
        "#f0d6ce",
        "#dce9e4",
        "#70808d",
        "#afbdc8",
        "#24313a",
        "#71808d",
        "#fffaf3",
        "#ede3d7",
        "#cc7259",
        "#4a8f7b",
        "#d7a16f",
        "#915f43",
    ),
    Palette(
        "#f6f1ea",
        "#dfeaf0",
        "#eadbcc",
        "#d6e4ea",
        "#64747d",
        "#a7b6bd",
        "#28363d",
        "#758791",
        "#fff8ef",
        "#eee5d9",
        "#d06d54",
        "#5b87b8",
        "#daa96b",
        "#8c5b41",
    ),
]

DARK_PALETTES = [
    Palette(
        "#0d1722",
        "#1c2837",
        "#233647",
        "#14303d",
        "#7d90a0",
        "#485e6e",
        "#edf3f7",
        "#98a9b5",
        "#1c2833",
        "#21313f",
        "#ff9a75",
        "#71d0c8",
        "#db9e58",
        "#f6d0ad",
    ),
    Palette(
        "#0f1826",
        "#1d2736",
        "#263244",
        "#1e3340",
        "#8394a2",
        "#4f6170",
        "#eef4f7",
        "#99a8b1",
        "#1e2834",
        "#243141",
        "#ffa077",
        "#6ec2ff",
        "#dda463",
        "#f5d6ac",
    ),
    Palette(
        "#101923",
        "#1d2933",
        "#2a3444",
        "#173038",
        "#82939d",
        "#4c6167",
        "#eef4f6",
        "#97a7af",
        "#1e2b34",
        "#263642",
        "#f69679",
        "#7dd0a9",
        "#dca56a",
        "#f2d4af",
    ),
]


def slot_time(moment: datetime) -> datetime:
    return moment.replace(hour=(moment.hour // 4) * 4, minute=0, second=0, microsecond=0)


def build_seed(moment: datetime) -> int:
    material = moment.strftime("%Y-%m-%d-%H")
    return int(sha256(material.encode("utf-8")).hexdigest()[:16], 16)


def choose_palette(theme: str, moment: datetime) -> Palette:
    slot = (moment.timetuple().tm_yday + moment.hour // 4) % 3
    return (DARK_PALETTES if theme == "dark" else LIGHT_PALETTES)[slot]


def choose_variant(moment: datetime) -> Variant:
    rng = random.Random(build_seed(moment))
    return Variant(
        flip=-1 if rng.random() < 0.5 else 1,
        cat_x=480 + rng.uniform(-18, 18),
        cat_y=208 + rng.uniform(-4, 4),
        ball_distance=186 + rng.uniform(-8, 18),
        arch_rx=226 + rng.uniform(-26, 30),
        arch_control_y=150 + rng.uniform(-12, 10),
        arc_drift=rng.uniform(-10, 10),
        glow_x=rng.uniform(-36, 34),
        glow_y=rng.uniform(-12, 16),
        secondary_glow=rng.random() > 0.45,
        accent_index=rng.randrange(2),
        micro_phase=rng.uniform(0, 4),
    )


def fmt(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        return str(int(round(value)))
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def pair_values(values: list[tuple[float, float]]) -> str:
    return ";".join(f"{fmt(x)} {fmt(y)}" for x, y in values)


def scalar_values(values: list[float]) -> str:
    return ";".join(fmt(value) for value in values)


def rotate_values(values: list[float]) -> str:
    return ";".join(f"{fmt(value)} 0 0" for value in values)


def animate_attribute(name: str, values: str, *, dur: float = CYCLE, key_times: str = KEY_TIMES) -> str:
    return (
        f'<animate attributeName="{name}" values="{values}" keyTimes="{key_times}" '
        f'dur="{fmt(dur)}s" repeatCount="indefinite" />'
    )


def animate_transform(
    transform_type: str,
    values: str,
    *,
    dur: float = CYCLE,
    key_times: str = KEY_TIMES,
    additive: str | None = None,
) -> str:
    additive_attr = f' additive="{additive}"' if additive else ""
    return (
        f'<animateTransform attributeName="transform" type="{transform_type}" values="{values}" '
        f'keyTimes="{key_times}" dur="{fmt(dur)}s" repeatCount="indefinite"{additive_attr} />'
    )


def build_stage(palette: Palette, variant: Variant, accent: str) -> str:
    arch_left = variant.cat_x - variant.arch_rx
    arch_right = variant.cat_x + variant.arch_rx
    arc_y = 302
    secondary_arc_y = variant.arch_control_y + 24

    optional_glow = ""
    if variant.secondary_glow:
        optional_glow = f"""
    <ellipse cx="{fmt(variant.cat_x + 92)}" cy="{fmt(208 + variant.glow_y)}" rx="132" ry="82"
             fill="{palette.haze_secondary}" opacity="0.22" />"""

    return f"""
  <g filter="url(#blur)">
    <ellipse cx="{fmt(variant.cat_x + variant.glow_x)}" cy="{fmt(206 + variant.glow_y)}" rx="172" ry="112"
             fill="{palette.haze}" opacity="0.28" />
{optional_glow}
  </g>

  <g>
    <ellipse cx="{fmt(variant.cat_x)}" cy="330" rx="244" ry="36" fill="{palette.stage_soft}" opacity="0.46" />
    <path d="M 170 312 C 284 {fmt(304 + variant.arc_drift)} 676 {fmt(304 - variant.arc_drift)} 790 312"
          class="stage-line" />
    <path d="M {fmt(arch_left)} {arc_y} Q {fmt(variant.cat_x)} {fmt(variant.arch_control_y)} {fmt(arch_right)} {arc_y}"
          class="frame-line" />
    <path d="M {fmt(arch_left + 24)} {arc_y} Q {fmt(variant.cat_x)} {fmt(secondary_arc_y)} {fmt(arch_right - 24)} {arc_y}"
          class="frame-line soft" />
    <path d="M {fmt(variant.cat_x - 138)} 294 Q {fmt(variant.cat_x)} 282 {fmt(variant.cat_x + 138)} 294"
          stroke="{accent}" stroke-opacity="0.18" stroke-width="1.6" stroke-linecap="round" fill="none">
      <animate attributeName="stroke-opacity" values="0.10;0.22;0.10" dur="11.5s" begin="-{fmt(variant.micro_phase)}s" repeatCount="indefinite" />
    </path>
  </g>"""


def build_cat(palette: Palette, variant: Variant, accent: str) -> str:
    jump_translate = pair_values(
        [(0, 0), (0, 0), (0, -2), (0, 0), (0, 0), (10, -18), (16, -2), (0, 0)]
    )
    jump_rotate = rotate_values([0, 0, 0, -1, 0, -3, 2, 0])
    head_translate = pair_values([(0, 6), (0, 6), (4, -4), (-12, 12), (4, 0), (6, -2), (2, 4), (0, 6)])
    head_rotate = rotate_values([6, 6, -18, -34, -6, 8, 10, 6])
    rest_paw_opacity = scalar_values([1, 1, 0.7, 0.08, 0.22, 0.56, 1, 1])
    groom_paw_opacity = scalar_values([0, 0, 0.22, 1, 0, 0, 0, 0])
    play_paw_opacity = scalar_values([0, 0, 0, 0, 1, 0.42, 0, 0])
    sleep_eyes_opacity = scalar_values([1, 1, 0, 0, 0, 0, 1, 1])
    open_eyes_opacity = scalar_values([0, 0, 0.48, 0.42, 1, 0.92, 0, 0])
    mouth_line_opacity = scalar_values([1, 1, 0, 0.12, 0.3, 0.1, 1, 1])
    yawn_opacity = scalar_values([0, 0, 0.94, 0, 0, 0, 0, 0])
    yawn_ry = scalar_values([0, 0, 12, 2, 0, 0, 0, 0])
    tongue_opacity = scalar_values([0, 0, 0, 0.76, 0, 0, 0, 0])
    ball_translate = pair_values([(0, 0), (0, 0), (0, 0), (0, 0), (18, -4), (34, -1), (12, 0), (0, 0)])
    ball_rotate = rotate_values([0, 0, 0, 0, 120, 270, 360, 360])
    blink_timeline = "0;0.53;0.545;0.56;0.63;0.645;1"
    breath_begin = f"-{fmt(variant.micro_phase)}s"
    tail_begin = f"-{fmt(variant.micro_phase + 0.8)}s"
    ear_begin = f"-{fmt(variant.micro_phase + 1.6)}s"

    return f"""
  <g transform="translate({fmt(variant.cat_x)} {fmt(variant.cat_y)})">
    <g transform="scale({variant.flip} 1)">
      <g>
        {animate_transform("translate", jump_translate)}
        <g>
          {animate_transform("rotate", jump_rotate)}
          <g>
            <animateTransform attributeName="transform" type="translate" values="0 0;0 -1.8;0 0"
                              dur="4.8s" begin="{breath_begin}" repeatCount="indefinite" />

            <ellipse cx="8" cy="118" rx="162" ry="20" fill="{palette.stage}" fill-opacity="0.16" />

            <g transform="translate(0 0)">
              <path d="M -118 56 C -108 8 -18 -10 72 18 C 112 30 132 64 120 84 C 106 100 54 102 4 94 C -56 84 -100 82 -118 56 Z"
                    fill="{palette.cat_fill}" />
              <path d="M -118 56 C -108 8 -18 -10 72 18 C 112 30 132 64 120 84 C 106 100 54 102 4 94 C -56 84 -100 82 -118 56 Z"
                    class="cat-line" />
              <path d="M -92 48 C -70 18 -18 8 72 26" class="cat-line soft" />
              <path d="M -16 74 C 18 82 58 84 94 78" class="cat-line soft" />
              <path d="M -22 76 C -38 90 -18 100 14 94" class="cat-line soft" />
              <path d="M 64 54 C 74 66 74 84 62 92" class="cat-line soft" />
            </g>

            <g opacity="0.96">
              <path d="M 68 78 C 84 88 90 96 92 108" class="cat-line" />
              <path d="M 90 80 C 100 90 102 98 100 108" class="cat-line" />
              {animate_attribute("opacity", rest_paw_opacity)}
            </g>

            <g opacity="0">
              <path d="M 70 78 C 82 60 88 40 86 18 C 86 4 92 -4 102 -8" class="cat-line" />
              {animate_attribute("opacity", groom_paw_opacity)}
              <animateTransform attributeName="transform" type="translate" values="0 0;-2 -4;0 0;2 -2;0 0"
                                dur="1.8s" begin="{breath_begin}" repeatCount="indefinite" />
            </g>

            <g opacity="0">
              <path d="M 68 78 C 98 72 132 74 154 86" class="cat-line" />
              {animate_attribute("opacity", play_paw_opacity)}
              <animateTransform attributeName="transform" type="translate" values="0 0;2 -2;0 0"
                                dur="2.6s" begin="{tail_begin}" repeatCount="indefinite" />
            </g>

            <g transform="translate(-108 58)">
              <path d="M 0 0 C -34 -42 -92 -18 -82 26 C -76 56 -36 44 -18 26" class="tail-line" />
              <animateTransform attributeName="transform" type="rotate" values="10 0 0;6 0 0;-4 0 0;7 0 0;10 0 0"
                                dur="7.4s" begin="{tail_begin}" repeatCount="indefinite" />
              <g transform="translate(-70 16)">
                <path d="M 0 0 C -12 6 -14 18 -4 28" class="tail-tip" />
                <animateTransform attributeName="transform" type="rotate" values="-10 0 0;12 0 0;-6 0 0"
                                  dur="4.8s" begin="{ear_begin}" repeatCount="indefinite" />
              </g>
            </g>

            <g transform="translate(98 12)">
              {animate_transform("translate", head_translate)}
              <g>
                {animate_transform("rotate", head_rotate)}
                <g>
                  <circle cx="0" cy="0" r="34" fill="{palette.cat_fill}" />
                  <circle cx="0" cy="0" r="34" class="cat-line" />

                  <g transform="translate(-12 -20)">
                    <path d="M 0 0 L 8 -28 L 18 -2 Z" fill="{palette.cat_fill_soft}" stroke="{palette.line}" stroke-width="3" stroke-linejoin="round" />
                    <path d="M 7 -4 L 10 -18 L 14 -4" stroke="{accent}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.36" fill="none" />
                    <animateTransform attributeName="transform" type="rotate" values="0 -12 -20;0 -12 -20;7 -12 -20;0 -12 -20;0 -12 -20"
                                      keyTimes="0;0.56;0.6;0.64;1" dur="11.2s" begin="{ear_begin}" repeatCount="indefinite" />
                  </g>
                  <g transform="translate(12 -18)">
                    <path d="M 0 0 L 12 -30 L 20 -2 Z" fill="{palette.cat_fill_soft}" stroke="{palette.line}" stroke-width="3" stroke-linejoin="round" />
                    <path d="M 8 -4 L 12 -20 L 16 -4" stroke="{accent}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.28" fill="none" />
                    <animateTransform attributeName="transform" type="rotate" values="0 12 -18;0 12 -18;-6 12 -18;0 12 -18;0 12 -18"
                                      keyTimes="0;0.42;0.46;0.5;1" dur="9.6s" begin="{ear_begin}" repeatCount="indefinite" />
                  </g>

                  <g opacity="0">
                    <path d="M -6 -2 Q 2 2 10 -2" class="face-line" />
                    <path d="M 14 -2 Q 22 2 30 -2" class="face-line" />
                    {animate_attribute("opacity", sleep_eyes_opacity)}
                  </g>

                  <g opacity="0">
                    <path d="M -6 -4 L 10 -4" class="face-line" />
                    <path d="M 14 -4 L 30 -4" class="face-line" />
                    {animate_attribute("opacity", open_eyes_opacity)}
                  </g>

                  <g opacity="0">
                    <path d="M -6 -2 Q 2 1 10 -2" class="face-line" />
                    <path d="M 14 -2 Q 22 1 30 -2" class="face-line" />
                    <animate attributeName="opacity" values="0;0;0.9;0;0;0.9;0"
                             keyTimes="{blink_timeline}" dur="{CYCLE}s" repeatCount="indefinite" />
                  </g>

                  <path d="M 30 4 L 38 8 L 30 12 Z" fill="{accent}" fill-opacity="0.72" />
                  <path d="M 26 16 Q 33 20 40 16" class="face-line" opacity="0">
                    {animate_attribute("opacity", mouth_line_opacity)}
                  </path>
                  <ellipse cx="34" cy="18" rx="6" ry="0" fill="{accent}" fill-opacity="0.16" stroke="{palette.line}" stroke-width="2.3" opacity="0">
                    {animate_attribute("opacity", yawn_opacity)}
                    {animate_attribute("ry", yawn_ry)}
                  </ellipse>
                  <path d="M 30 18 C 34 26 40 28 44 24" stroke="{accent}" stroke-width="2.4" stroke-linecap="round" fill="none" opacity="0">
                    {animate_attribute("opacity", tongue_opacity)}
                  </path>

                  <path d="M 34 10 L 56 6" class="whisker-line" />
                  <path d="M 34 14 L 58 14" class="whisker-line" />
                  <path d="M 34 18 L 56 22" class="whisker-line" />
                </g>
              </g>
            </g>
          </g>
        </g>
      </g>

      <g transform="translate({fmt(variant.ball_distance)} 92)">
        {animate_transform("translate", ball_translate)}
        <g>
          {animate_transform("rotate", ball_rotate)}
          <circle cx="0" cy="0" r="19" fill="{palette.yarn_fill}" fill-opacity="0.24" stroke="{palette.yarn_line}" stroke-width="2.6" />
          <path d="M -12 -4 C -4 -10 8 -10 12 -2 C 14 4 8 10 -2 11" stroke="{palette.yarn_line}" stroke-width="2.2" stroke-linecap="round" fill="none" />
          <path d="M -15 5 C -7 0 1 0 6 6" stroke="{accent}" stroke-width="1.8" stroke-linecap="round" fill="none" opacity="0.52" />
          <path d="M -18 5 C -28 2 -36 4 -44 10" stroke="{palette.yarn_line}" stroke-width="1.9" stroke-linecap="round" fill="none" opacity="0.56" />
          <circle cx="0" cy="0" r="2.2" fill="{accent}" />
        </g>
      </g>
    </g>
  </g>"""


def render_svg(theme: str, moment: datetime) -> str:
    palette = choose_palette(theme, moment)
    variant = choose_variant(moment)
    accent = palette.accent_b if variant.accent_index else palette.accent_a
    stage = build_stage(palette, variant, accent)
    cat = build_cat(palette, variant, accent)

    return f"""<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">Animated line-art cat resting on an abstract stage</title>
  <desc id="desc">A calm profile cover where a minimalist cat sleeps, yawns, grooms, nudges a yarn ball, makes a small jump, and settles back into rest.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="{WIDTH}" y2="{HEIGHT}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{palette.background_start}" />
      <stop offset="100%" stop-color="{palette.background_end}" />
    </linearGradient>
    <filter id="blur" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="26" />
    </filter>
    <style>
      .stage-line {{
        fill: none;
        stroke: {palette.stage};
        stroke-width: 2;
        stroke-linecap: round;
      }}
      .frame-line {{
        fill: none;
        stroke: {palette.line_soft};
        stroke-opacity: 0.28;
        stroke-width: 1.8;
        stroke-linecap: round;
      }}
      .frame-line.soft {{
        stroke-opacity: 0.14;
      }}
      .cat-line {{
        fill: none;
        stroke: {palette.line};
        stroke-width: 3.4;
        stroke-linecap: round;
        stroke-linejoin: round;
      }}
      .cat-line.soft {{
        stroke-width: 2.4;
        stroke: {palette.line_soft};
        stroke-opacity: 0.88;
      }}
      .face-line {{
        fill: none;
        stroke: {palette.line};
        stroke-width: 2.4;
        stroke-linecap: round;
        stroke-linejoin: round;
      }}
      .whisker-line {{
        fill: none;
        stroke: {palette.line_soft};
        stroke-width: 1.8;
        stroke-linecap: round;
      }}
      .tail-line {{
        fill: none;
        stroke: {palette.line};
        stroke-width: 10;
        stroke-linecap: round;
        stroke-linejoin: round;
      }}
      .tail-tip {{
        fill: none;
        stroke: {accent};
        stroke-width: 3.2;
        stroke-linecap: round;
        stroke-linejoin: round;
        opacity: 0.64;
      }}
    </style>
  </defs>

  <rect width="{WIDTH}" height="{HEIGHT}" rx="28" fill="url(#bg)" />

{stage}
{cat}
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
