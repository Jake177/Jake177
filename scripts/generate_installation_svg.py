#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import math
from pathlib import Path
import random

WIDTH = 960
HEIGHT = 420

FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "J": ["00111", "00010", "00010", "00010", "10010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
}


@dataclass(frozen=True)
class Palette:
    background_start: str
    background_end: str
    haze: str
    contour: str
    secondary: str
    accent: str
    particle: str
    label: str


DARK_PALETTES = [
    Palette("#050816", "#0d2434", "#123f48", "#8ccfff", "#4ce0b3", "#ff8a5b", "#fff5db", "#cdd8e7"),
    Palette("#07101f", "#172544", "#45204f", "#9ab7ff", "#4de2c5", "#ffd166", "#fff7e6", "#dce5f1"),
    Palette("#03141b", "#17313f", "#3f2945", "#97dffd", "#8affd2", "#ff9e7a", "#fff3e0", "#d6e2ee"),
]

LIGHT_PALETTES = [
    Palette("#f7f2ea", "#ddeef3", "#f2d8cc", "#245168", "#3aa287", "#d9734e", "#163143", "#34515e"),
    Palette("#fcf8ef", "#e3ecfb", "#f0dbc7", "#3a5679", "#3e9c88", "#c76743", "#1f3042", "#465865"),
    Palette("#f6f0e8", "#dce7ed", "#ead4da", "#35536b", "#3d9988", "#c76e57", "#213447", "#425663"),
]


def build_seed(moment: datetime, theme: str) -> int:
    material = f"{moment.strftime('%Y-%m-%d-%H')}::{theme}"
    return int(sha256(material.encode("utf-8")).hexdigest()[:16], 16)


def choose_palette(theme: str, moment: datetime) -> Palette:
    slot = (moment.timetuple().tm_yday + moment.hour // 4) % 3
    return (DARK_PALETTES if theme == "dark" else LIGHT_PALETTES)[slot]


def text_points(text: str, cell: float) -> list[tuple[float, float]]:
    glyph_width = 6
    total_cols = len(text) * glyph_width - 1
    start_x = WIDTH / 2 - ((total_cols - 1) * cell) / 2
    start_y = HEIGHT / 2 - (6 * cell) / 2 + 6
    points: list[tuple[float, float]] = []

    for index, char in enumerate(text):
        pattern = FONT[char]
        offset_col = index * glyph_width
        for row, line in enumerate(pattern):
            for col, pixel in enumerate(line):
                if pixel == "1":
                    points.append((start_x + (offset_col + col) * cell, start_y + row * cell))
    return points


def wave_y(x: float, base_y: float, phase: float, freq_a: float, freq_b: float, amp_a: float, amp_b: float) -> float:
    return (
        base_y
        + math.sin(x * freq_a + phase) * amp_a
        + math.cos(x * freq_b - phase * 1.3) * amp_b
    )


def build_wave_path(index: int, variant: int, rng: random.Random) -> str:
    points = 20
    base_y = 48 + index * 22
    phase = index * 0.37 + variant * 0.65 + rng.uniform(-0.25, 0.25)
    freq_a = 0.010 + index * 0.00055
    freq_b = 0.022 + index * 0.00035
    amp_a = 9 + index * 0.7 + variant * 1.3
    amp_b = 4 + variant * 0.7
    path_parts: list[str] = []

    for point_index in range(points):
        x = WIDTH * point_index / (points - 1)
        y = wave_y(x, base_y, phase, freq_a, freq_b, amp_a, amp_b)
        command = "M" if point_index == 0 else "L"
        path_parts.append(f"{command} {x:.2f} {y:.2f}")

    return " ".join(path_parts)


def build_contours(palette: Palette, rng: random.Random) -> str:
    lines: list[str] = []
    gradient_ids = ["contourA", "contourB", "contourC"]

    for index in range(12):
        path_a = build_wave_path(index, 0, rng)
        path_b = build_wave_path(index, 1, rng)
        duration = 18 + index * 1.7
        dash = 40 + index * 3
        gradient_id = gradient_ids[index % len(gradient_ids)]
        lines.append(
            f"""
      <path d="{path_a}" stroke="url(#{gradient_id})" stroke-width="1.1" stroke-linecap="round"
            stroke-dasharray="{dash} {dash + 18}" opacity="{0.10 + index * 0.022:.3f}">
        <animate attributeName="d" values="{path_a};{path_b};{path_a}" dur="{duration:.1f}s" repeatCount="indefinite" />
        <animate attributeName="stroke-dashoffset" values="0;{dash * -2};0" dur="{duration * 1.2:.1f}s" repeatCount="indefinite" />
      </path>"""
        )
    return "\n".join(lines)


def build_haze(palette: Palette, rng: random.Random) -> str:
    ellipses: list[str] = []

    for index in range(3):
        cx = 160 + index * 280 + rng.uniform(-30, 30)
        cy = 120 + (index % 2) * 120 + rng.uniform(-20, 20)
        rx = 170 + index * 22
        ry = 110 + index * 12
        drift = 40 + index * 14
        duration = 22 + index * 6
        opacity = 0.10 if index != 1 else 0.15
        ellipses.append(
            f"""
      <ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{palette.haze}" opacity="{opacity:.2f}">
        <animate attributeName="cx" values="{cx - drift:.1f};{cx + drift:.1f};{cx - drift:.1f}" dur="{duration}s" repeatCount="indefinite" />
        <animate attributeName="cy" values="{cy + drift / 3:.1f};{cy - drift / 3:.1f};{cy + drift / 3:.1f}" dur="{duration + 6}s" repeatCount="indefinite" />
      </ellipse>"""
        )

    return "\n".join(ellipses)


def polar_point(cx: float, cy: float, radius: float, angle_deg: float) -> tuple[float, float]:
    angle = math.radians(angle_deg)
    return cx + math.cos(angle) * radius, cy + math.sin(angle) * radius


def build_panel_grid(palette: Palette) -> str:
    lines: list[str] = []

    for x in range(84, WIDTH, 84):
        lines.append(
            f"""
      <line x1="{x}" y1="34" x2="{x}" y2="{HEIGHT - 34}" stroke="{palette.label}" stroke-width="0.85"
            stroke-opacity="0.06" stroke-dasharray="3 10">
        <animate attributeName="stroke-dashoffset" values="0;-26" dur="{28 + (x % 5) * 3}s" repeatCount="indefinite" />
      </line>"""
        )

    for y in range(64, HEIGHT, 52):
        lines.append(
            f"""
      <line x1="34" y1="{y}" x2="{WIDTH - 34}" y2="{y}" stroke="{palette.label}" stroke-width="0.8"
            stroke-opacity="0.07" stroke-dasharray="4 11">
        <animate attributeName="stroke-dashoffset" values="0;30" dur="{22 + (y % 4) * 4}s" repeatCount="indefinite" />
      </line>"""
        )

    return "\n".join(lines)


def build_corner_brackets(palette: Palette) -> str:
    color = palette.label
    size = 26
    edge = 36
    points = [
        (edge, edge, 1, 1),
        (WIDTH - edge, edge, -1, 1),
        (edge, HEIGHT - edge, 1, -1),
        (WIDTH - edge, HEIGHT - edge, -1, -1),
    ]
    brackets: list[str] = []

    for x, y, dx, dy in points:
        brackets.append(
            f"""
      <path d="M {x} {y + dy * size} L {x} {y} L {x + dx * size} {y}"
            stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-opacity="0.30" />"""
        )

    return "\n".join(brackets)


def build_tick_ring(
    cx: float,
    cy: float,
    radius: float,
    count: int,
    palette: Palette,
    opacity: float,
    inner_offset: float,
    outer_offset: float,
    duration: float | None = None,
    reverse: bool = False,
) -> str:
    ticks: list[str] = []

    for index in range(count):
        angle = index * 360 / count
        x1, y1 = polar_point(cx, cy, radius - inner_offset, angle)
        x2, y2 = polar_point(cx, cy, radius + outer_offset, angle)
        stroke_width = 1.35 if index % max(1, count // 12) == 0 else 0.75
        tick_opacity = opacity * (1.22 if stroke_width > 1 else 0.78)
        ticks.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{palette.label}" stroke-width="{stroke_width:.2f}" stroke-opacity="{tick_opacity:.3f}" />'
        )

    body = "\n      ".join(ticks)
    if duration is None:
        return f"\n    <g>\n      {body}\n    </g>"

    angle_to = "-360" if reverse else "360"
    return f"""
    <g>
      {body}
      <animateTransform attributeName="transform" type="rotate"
                        from="0 {cx} {cy}" to="{angle_to} {cx} {cy}"
                        dur="{duration:.1f}s" repeatCount="indefinite" />
    </g>"""


def build_mechanical_core(palette: Palette) -> str:
    cx = WIDTH / 2
    cy = HEIGHT / 2 + 2

    return f"""
    <g>
      <circle cx="{cx}" cy="{cy}" r="132" stroke="{palette.label}" stroke-width="1.1" stroke-opacity="0.18" />
      <circle cx="{cx}" cy="{cy}" r="116" stroke="{palette.contour}" stroke-width="0.9"
              stroke-dasharray="10 18" stroke-opacity="0.18">
        <animate attributeName="stroke-dashoffset" values="0;112" dur="34s" repeatCount="indefinite" />
      </circle>
      <circle cx="{cx}" cy="{cy}" r="92" stroke="{palette.secondary}" stroke-width="1.1"
              stroke-dasharray="28 14 8 20" stroke-opacity="0.28">
        <animateTransform attributeName="transform" type="rotate"
                          from="0 {cx} {cy}" to="360 {cx} {cy}"
                          dur="48s" repeatCount="indefinite" />
      </circle>
      <circle cx="{cx}" cy="{cy}" r="60" stroke="{palette.accent}" stroke-width="0.95"
              stroke-dasharray="6 12" stroke-opacity="0.28">
        <animateTransform attributeName="transform" type="rotate"
                          from="0 {cx} {cy}" to="-360 {cx} {cy}"
                          dur="26s" repeatCount="indefinite" />
      </circle>
      {build_tick_ring(cx, cy, 122, 72, palette, 0.24, 6, 4)}
      {build_tick_ring(cx, cy, 88, 36, palette, 0.22, 5, 4, duration=40, reverse=True)}
      <line x1="{cx - 154}" y1="{cy}" x2="{cx + 154}" y2="{cy}" stroke="{palette.label}" stroke-width="0.9" stroke-opacity="0.12" />
      <line x1="{cx}" y1="{cy - 154}" x2="{cx}" y2="{cy + 154}" stroke="{palette.label}" stroke-width="0.9" stroke-opacity="0.10" />
      <rect x="{cx - 26}" y="{cy - 26}" width="52" height="52" rx="8"
            stroke="{palette.secondary}" stroke-width="1.2" stroke-opacity="0.32" fill="none" />
      <rect x="{cx - 12}" y="{cy - 12}" width="24" height="24" rx="4"
            fill="{palette.particle}" fill-opacity="0.14" stroke="{palette.label}" stroke-opacity="0.24" />
      <path d="M {cx - 18} {cy - 68} L {cx - 18} {cy - 96} L {cx + 18} {cy - 96} L {cx + 18} {cy - 68}"
            stroke="{palette.label}" stroke-width="1.0" stroke-opacity="0.26" fill="none" />
      <path d="M {cx - 18} {cy + 68} L {cx - 18} {cy + 96} L {cx + 18} {cy + 96} L {cx + 18} {cy + 68}"
            stroke="{palette.label}" stroke-width="1.0" stroke-opacity="0.26" fill="none" />
      <path d="M {cx - 68} {cy - 18} L {cx - 96} {cy - 18} L {cx - 96} {cy + 18} L {cx - 68} {cy + 18}"
            stroke="{palette.label}" stroke-width="1.0" stroke-opacity="0.26" fill="none" />
      <path d="M {cx + 68} {cy - 18} L {cx + 96} {cy - 18} L {cx + 96} {cy + 18} L {cx + 68} {cy + 18}"
            stroke="{palette.label}" stroke-width="1.0" stroke-opacity="0.26" fill="none" />
      <g>
        <line x1="{cx}" y1="{cy}" x2="{cx + 108}" y2="{cy - 28}" stroke="{palette.accent}" stroke-width="1.3" stroke-opacity="0.55" />
        <circle cx="{cx + 108}" cy="{cy - 28}" r="4.0" fill="{palette.accent}" fill-opacity="0.88" />
        <animateTransform attributeName="transform" type="rotate"
                          from="0 {cx} {cy}" to="360 {cx} {cy}"
                          dur="24s" repeatCount="indefinite" />
      </g>
      <g>
        <line x1="{cx}" y1="{cy}" x2="{cx - 76}" y2="{cy + 18}" stroke="{palette.secondary}" stroke-width="1.1" stroke-opacity="0.48" />
        <circle cx="{cx - 76}" cy="{cy + 18}" r="3.0" fill="{palette.secondary}" fill-opacity="0.86" />
        <animateTransform attributeName="transform" type="rotate"
                          from="0 {cx} {cy}" to="-360 {cx} {cy}"
                          dur="16s" repeatCount="indefinite" />
      </g>
    </g>"""


def build_aux_module(cx: float, cy: float, radius: float, palette: Palette, duration: float, reverse: bool = False) -> str:
    direction = "-360" if reverse else "360"
    return f"""
    <g>
      <rect x="{cx - radius - 22:.1f}" y="{cy - radius - 18:.1f}" width="{radius * 2 + 44:.1f}" height="{radius * 2 + 36:.1f}" rx="18"
            stroke="{palette.label}" stroke-width="0.95" stroke-opacity="0.16" fill="none" />
      <circle cx="{cx}" cy="{cy}" r="{radius:.1f}" stroke="{palette.label}" stroke-width="1.0" stroke-opacity="0.22" />
      <circle cx="{cx}" cy="{cy}" r="{radius - 16:.1f}" stroke="{palette.contour}" stroke-width="0.9"
              stroke-dasharray="5 10" stroke-opacity="0.24">
        <animate attributeName="stroke-dashoffset" values="0;60" dur="{duration * 0.8:.1f}s" repeatCount="indefinite" />
      </circle>
      {build_tick_ring(cx, cy, radius - 6, 24, palette, 0.20, 3, 3)}
      <g>
        <line x1="{cx}" y1="{cy}" x2="{cx + radius - 10:.1f}" y2="{cy}" stroke="{palette.accent}" stroke-width="1.2" stroke-opacity="0.50" />
        <circle cx="{cx + radius - 10:.1f}" cy="{cy}" r="2.7" fill="{palette.accent}" fill-opacity="0.90" />
        <animateTransform attributeName="transform" type="rotate"
                          from="0 {cx} {cy}" to="{direction} {cx} {cy}"
                          dur="{duration:.1f}s" repeatCount="indefinite" />
      </g>
      <rect x="{cx - 11:.1f}" y="{cy - 11:.1f}" width="22" height="22" rx="4"
            fill="{palette.particle}" fill-opacity="0.12" stroke="{palette.label}" stroke-opacity="0.20" />
    </g>"""


def build_signal_bus(palette: Palette) -> str:
    y = HEIGHT / 2 + 2
    return f"""
    <g>
      <path d="M 118 {y} L 214 {y} L 266 {y - 30} L 346 {y - 30} L 388 {y}"
            stroke="{palette.secondary}" stroke-width="1.3" fill="none" stroke-opacity="0.34" stroke-dasharray="8 10">
        <animate attributeName="stroke-dashoffset" values="0;-72" dur="18s" repeatCount="indefinite" />
      </path>
      <path d="M 572 {y} L 614 {y - 30} L 694 {y - 30} L 746 {y} L 842 {y}"
            stroke="{palette.secondary}" stroke-width="1.3" fill="none" stroke-opacity="0.34" stroke-dasharray="8 10">
        <animate attributeName="stroke-dashoffset" values="0;72" dur="18s" repeatCount="indefinite" />
      </path>
      <line x1="388" y1="{y}" x2="572" y2="{y}" stroke="{palette.label}" stroke-width="1.0" stroke-opacity="0.16" stroke-dasharray="6 14" />
      <rect x="262" y="{y - 34}" width="88" height="8" rx="4" fill="{palette.label}" fill-opacity="0.07" />
      <rect x="610" y="{y - 34}" width="88" height="8" rx="4" fill="{palette.label}" fill-opacity="0.07" />
    </g>"""


def build_probe_pulses(palette: Palette, rng: random.Random) -> str:
    y = HEIGHT / 2 + 2
    pulses: list[str] = []
    rails = [
        ((118, y), (388, y)),
        ((572, y), (842, y)),
        ((WIDTH / 2, 58), (WIDTH / 2, HEIGHT - 58)),
    ]

    for index, ((x1, y1), (x2, y2)) in enumerate(rails):
        begin = index * 0.9
        duration = 7 + index * 1.8
        pulses.append(
            f"""
      <circle cx="{x1:.1f}" cy="{y1:.1f}" r="{2.4 + index * 0.4:.1f}" fill="{palette.accent}" fill-opacity="0.0">
        <animate attributeName="cx" values="{x1:.1f};{x2:.1f}" dur="{duration:.1f}s" begin="{begin:.1f}s" repeatCount="indefinite" />
        <animate attributeName="cy" values="{y1:.1f};{y2:.1f}" dur="{duration:.1f}s" begin="{begin:.1f}s" repeatCount="indefinite" />
        <animate attributeName="fill-opacity" values="0;0.84;0" dur="{duration:.1f}s" begin="{begin:.1f}s" repeatCount="indefinite" />
      </circle>"""
        )

    for index in range(10):
        x = rng.uniform(90, WIDTH - 90)
        y = rng.uniform(80, HEIGHT - 80)
        pulses.append(
            f"""
      <circle cx="{x:.2f}" cy="{y:.2f}" r="{rng.uniform(1.1, 2.0):.2f}" fill="{palette.secondary}" fill-opacity="{rng.uniform(0.10, 0.26):.2f}">
        <animate attributeName="fill-opacity" values="0.04;0.28;0.04" dur="{rng.uniform(8, 16):.1f}s" begin="{rng.uniform(0, 5):.1f}s" repeatCount="indefinite" />
      </circle>"""
        )

    return "\n".join(pulses)


def build_signature_nodes(palette: Palette, rng: random.Random) -> str:
    raw_points = text_points("JAKE", 6.2)[::4]
    xs = [point[0] for point in raw_points]
    ys = [point[1] for point in raw_points]
    center_x = WIDTH / 2
    center_y = HEIGHT / 2 - 8
    scale = min(154 / (max(xs) - min(xs)), 30 / (max(ys) - min(ys)))
    mapped: list[tuple[float, float]] = []

    for x, y in raw_points:
        nx = center_x + (x - (min(xs) + max(xs)) / 2) * scale
        ny = center_y + (y - (min(ys) + max(ys)) / 2) * scale
        mapped.append((nx, ny))

    traces: list[str] = []
    ordered = sorted(mapped, key=lambda point: (round(point[1] / 6), point[0]))

    for index in range(len(ordered) - 1):
        if index % 2 == 1:
            continue
        x1, y1 = ordered[index]
        x2, y2 = ordered[index + 1]
        bend_x = (x1 + x2) / 2 + rng.uniform(-6, 6)
        traces.append(
            f"""
      <path d="M {x1:.2f} {y1:.2f} L {bend_x:.2f} {y1:.2f} L {bend_x:.2f} {y2:.2f} L {x2:.2f} {y2:.2f}"
            stroke="{palette.secondary}" stroke-width="0.7" stroke-opacity="0.07" fill="none">
        <animate attributeName="stroke-opacity" values="0.02;0.09;0.02" dur="{11 + index * 0.3:.1f}s" begin="{index * 0.2:.1f}s" repeatCount="indefinite" />
      </path>"""
        )

    nodes = [
        f"""
      <rect x="{x - 1.3:.2f}" y="{y - 1.3:.2f}" width="2.6" height="2.6" rx="0.6"
            fill="{palette.particle}" fill-opacity="0.05" stroke="{palette.label}" stroke-width="0.5" stroke-opacity="0.08">
        <animate attributeName="fill-opacity" values="0.02;0.08;0.02" dur="{9 + (index % 8) * 0.9:.1f}s" begin="{index * 0.15:.1f}s" repeatCount="indefinite" />
      </rect>"""
        for index, (x, y) in enumerate(mapped)
    ]

    return f"""
    <g transform="rotate(-9 {center_x} {center_y})">
{''.join(traces)}
{''.join(nodes)}
    </g>"""


def render_svg(theme: str, moment: datetime) -> str:
    palette = choose_palette(theme, moment)
    rng = random.Random(build_seed(moment, theme))
    contours = build_contours(palette, rng)
    haze = build_haze(palette, rng)
    panel_grid = build_panel_grid(palette)
    brackets = build_corner_brackets(palette)
    core = build_mechanical_core(palette)
    module_left = build_aux_module(188, HEIGHT / 2 + 2, 42, palette, 19, reverse=False)
    module_right = build_aux_module(772, HEIGHT / 2 + 2, 54, palette, 23, reverse=True)
    signal_bus = build_signal_bus(palette)
    pulses = build_probe_pulses(palette, rng)
    signature_nodes = build_signature_nodes(palette, rng)
    label = moment.strftime("%Y.%m.%d %H:%M UTC")

    return f"""<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">Mechanical signal installation</title>
  <desc id="desc">Animated instrument-like artwork with rings, rails, gauges, and a faint embedded signature lattice.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="{WIDTH}" y2="{HEIGHT}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{palette.background_start}" />
      <stop offset="60%" stop-color="{palette.background_end}" />
      <stop offset="100%" stop-color="{palette.haze}" stop-opacity="0.82" />
    </linearGradient>
    <linearGradient id="contourA" x1="0" y1="0" x2="{WIDTH}" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{palette.contour}" stop-opacity="0.10" />
      <stop offset="50%" stop-color="{palette.secondary}" stop-opacity="0.75" />
      <stop offset="100%" stop-color="{palette.accent}" stop-opacity="0.12" />
    </linearGradient>
    <linearGradient id="contourB" x1="{WIDTH}" y1="0" x2="0" y2="{HEIGHT}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{palette.secondary}" stop-opacity="0.06" />
      <stop offset="55%" stop-color="{palette.contour}" stop-opacity="0.62" />
      <stop offset="100%" stop-color="{palette.accent}" stop-opacity="0.12" />
    </linearGradient>
    <linearGradient id="contourC" x1="0" y1="{HEIGHT}" x2="{WIDTH}" y2="60" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{palette.accent}" stop-opacity="0.08" />
      <stop offset="40%" stop-color="{palette.secondary}" stop-opacity="0.55" />
      <stop offset="100%" stop-color="{palette.contour}" stop-opacity="0.10" />
    </linearGradient>
    <filter id="blur" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="20" />
    </filter>
    <filter id="softGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="4" result="blurred" />
      <feMerge>
        <feMergeNode in="blurred" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>

  <rect width="{WIDTH}" height="{HEIGHT}" rx="28" fill="url(#bg)" />
  <rect x="20" y="20" width="{WIDTH - 40}" height="{HEIGHT - 40}" rx="24" stroke="{palette.label}" stroke-opacity="0.12" />

  <g filter="url(#blur)">
{haze}
  </g>

  <g>
{panel_grid}
{brackets}
  </g>

  <g>
{contours}
  </g>

  <g opacity="0.86">
    {signal_bus}
    {module_left}
    {module_right}
    {core}
  </g>

  <g filter="url(#softGlow)">
    {signature_nodes}
  </g>

  <g>
    {pulses}
  </g>

  <text x="40" y="{HEIGHT - 30}" fill="{palette.label}" fill-opacity="0.70"
        font-family="'Segoe UI', 'Noto Sans', sans-serif" font-size="13" letter-spacing="0.28em">KINETIC SIGNAL APPARATUS</text>
  <text x="{WIDTH - 192}" y="{HEIGHT - 30}" fill="{palette.label}" fill-opacity="0.42"
        font-family="'Segoe UI', 'Noto Sans', sans-serif" font-size="11" text-anchor="start" letter-spacing="0.18em">{label}</text>
</svg>
"""


def main() -> None:
    output_dir = Path("dist")
    output_dir.mkdir(parents=True, exist_ok=True)
    moment = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    outputs = {
        "signal-installation.svg": render_svg("light", moment),
        "signal-installation-dark.svg": render_svg("dark", moment),
    }

    for name, content in outputs.items():
        (output_dir / name).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
