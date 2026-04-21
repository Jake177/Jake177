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
            stroke-dasharray="{dash} {dash + 18}" opacity="{0.18 + index * 0.035:.3f}">
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
        opacity = 0.16 if index != 1 else 0.22
        ellipses.append(
            f"""
      <ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{palette.haze}" opacity="{opacity:.2f}">
        <animate attributeName="cx" values="{cx - drift:.1f};{cx + drift:.1f};{cx - drift:.1f}" dur="{duration}s" repeatCount="indefinite" />
        <animate attributeName="cy" values="{cy + drift / 3:.1f};{cy - drift / 3:.1f};{cy + drift / 3:.1f}" dur="{duration + 6}s" repeatCount="indefinite" />
      </ellipse>"""
        )

    return "\n".join(ellipses)


def build_orbit_group(cx: float, cy: float, radius: float, palette: Palette, duration: float, reverse: bool = False) -> str:
    direction = "-360" if reverse else "360"
    start = f"{cx} {cy}"
    ring_color = palette.secondary
    return f"""
    <g transform="translate({cx} {cy})" opacity="0.72">
      <circle cx="0" cy="0" r="{radius:.1f}" stroke="{ring_color}" stroke-width="1.1" stroke-dasharray="5 9" opacity="0.38" />
      <circle cx="0" cy="0" r="{radius - 16:.1f}" stroke="{palette.contour}" stroke-width="0.9" stroke-dasharray="3 10" opacity="0.24" />
      <circle cx="{radius:.1f}" cy="0" r="3.2" fill="{palette.accent}" opacity="0.85" />
      <circle cx="{-(radius - 16):.1f}" cy="0" r="2.3" fill="{palette.particle}" opacity="0.92" />
      <animateTransform attributeName="transform" attributeType="XML"
                        type="rotate" from="0 {start}" to="{direction} {start}"
                        dur="{duration:.1f}s" repeatCount="indefinite" additive="sum" />
    </g>"""


def build_connector_lines(targets: list[tuple[float, float]], palette: Palette, rng: random.Random) -> str:
    ordered = sorted(targets, key=lambda point: (point[1], point[0]))
    stride = max(1, len(ordered) // 16)
    chosen = ordered[::stride][:16]
    lines: list[str] = []

    for index in range(len(chosen) - 1):
        x1, y1 = chosen[index]
        x2, y2 = chosen[index + 1]
        mid_x = (x1 + x2) / 2 + rng.uniform(-14, 14)
        mid_y = (y1 + y2) / 2 + rng.uniform(-10, 10)
        delay = index * 0.35
        duration = 9 + index * 0.7
        lines.append(
            f"""
      <path d="M {x1:.1f} {y1:.1f} Q {mid_x:.1f} {mid_y:.1f} {x2:.1f} {y2:.1f}"
            stroke="{palette.secondary}" stroke-width="0.9" fill="none" opacity="0.0">
        <animate attributeName="opacity" values="0;0.32;0.18;0" dur="{duration:.1f}s" begin="{delay:.1f}s" repeatCount="indefinite" />
      </path>"""
        )

    return "\n".join(lines)


def build_text_particles(targets: list[tuple[float, float]], palette: Palette, rng: random.Random) -> str:
    particles: list[str] = []

    for index, (target_x, target_y) in enumerate(targets):
        origin_x = target_x + rng.uniform(-170, 170)
        origin_y = target_y + rng.uniform(-110, 110)
        drift_x = target_x + rng.uniform(-8, 8)
        drift_y = target_y + rng.uniform(-8, 8)
        begin = rng.uniform(0, 8)
        duration = 14 + (index % 9) * 1.1
        radius = 1.4 + (index % 3) * 0.45
        opacity_peak = 0.5 + (index % 4) * 0.09
        particles.append(
            f"""
      <circle cx="{origin_x:.2f}" cy="{origin_y:.2f}" r="{radius:.2f}" fill="{palette.particle}" opacity="0.0">
        <animate attributeName="cx" values="{origin_x:.2f};{target_x:.2f};{drift_x:.2f};{origin_x:.2f}" keyTimes="0;0.34;0.68;1"
                 dur="{duration:.1f}s" begin="{begin:.2f}s" repeatCount="indefinite" />
        <animate attributeName="cy" values="{origin_y:.2f};{target_y:.2f};{drift_y:.2f};{origin_y:.2f}" keyTimes="0;0.34;0.68;1"
                 dur="{duration:.1f}s" begin="{begin:.2f}s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;{opacity_peak:.2f};{opacity_peak:.2f};0" keyTimes="0;0.28;0.70;1"
                 dur="{duration:.1f}s" begin="{begin:.2f}s" repeatCount="indefinite" />
      </circle>"""
        )

    return "\n".join(particles)


def build_ambient_particles(palette: Palette, rng: random.Random) -> str:
    particles: list[str] = []

    for index in range(28):
        x = rng.uniform(24, WIDTH - 24)
        y = rng.uniform(36, HEIGHT - 36)
        drift_x = x + rng.uniform(-45, 45)
        drift_y = y + rng.uniform(-34, 34)
        radius = rng.uniform(1.0, 2.4)
        duration = rng.uniform(12, 24)
        begin = rng.uniform(0, 6)
        opacity = rng.uniform(0.14, 0.36)
        particles.append(
            f"""
      <circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="{palette.accent}" opacity="{opacity:.2f}">
        <animate attributeName="cx" values="{x:.2f};{drift_x:.2f};{x:.2f}" dur="{duration:.1f}s" begin="{begin:.2f}s" repeatCount="indefinite" />
        <animate attributeName="cy" values="{y:.2f};{drift_y:.2f};{y:.2f}" dur="{duration + 4:.1f}s" begin="{begin:.2f}s" repeatCount="indefinite" />
      </circle>"""
        )

    return "\n".join(particles)


def render_svg(theme: str, moment: datetime) -> str:
    palette = choose_palette(theme, moment)
    rng = random.Random(build_seed(moment, theme))
    targets = text_points("JAKE", 13.5)
    contours = build_contours(palette, rng)
    haze = build_haze(palette, rng)
    text_particle_layer = build_text_particles(targets, palette, rng)
    ambient_particles = build_ambient_particles(palette, rng)
    connectors = build_connector_lines(targets, palette, rng)
    orbit_left = build_orbit_group(188, 130, 56, palette, 32, reverse=False)
    orbit_right = build_orbit_group(772, 292, 72, palette, 44, reverse=True)
    label = moment.strftime("%Y.%m.%d %H:%M UTC")

    return f"""<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">Ambient profile installation</title>
  <desc id="desc">Animated contour lines, orbiting rings, and drifting particles that briefly assemble into the name JAKE.</desc>
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
      <feGaussianBlur stdDeviation="28" />
    </filter>
    <filter id="softGlow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="5" result="blurred" />
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
{contours}
  </g>

  <g opacity="0.75">
    {orbit_left}
    {orbit_right}
  </g>

  <g filter="url(#softGlow)">
{connectors}
{text_particle_layer}
  </g>

  <g>
{ambient_particles}
  </g>

  <text x="40" y="{HEIGHT - 30}" fill="{palette.label}" fill-opacity="0.70"
        font-family="'Segoe UI', 'Noto Sans', sans-serif" font-size="13" letter-spacing="0.28em">AMBIENT INSTALLATION</text>
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
