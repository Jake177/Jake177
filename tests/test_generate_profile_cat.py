from pathlib import Path
import json
import tempfile
import unittest

from PIL import Image

from scripts import generate_profile_cat


class ProfilePetMapTests(unittest.TestCase):
    def write_fixture(self, root: Path, frame_count: int = 2) -> Path:
        sprite = Image.new("RGBA", (frame_count * 8, 8), (0, 0, 0, 0))
        for index, color in enumerate(((255, 0, 0, 255), (0, 0, 255, 255))[:frame_count]):
            frame = Image.new("RGBA", (8, 8), color)
            sprite.alpha_composite(frame, (index * 8, 0))
        sprite.save(root / "spritesheet.webp")

        map_path = root / "profile-map.json"
        map_path.write_text(
            json.dumps(
                {
                    "spritesheet": "spritesheet.webp",
                    "frameWidth": 8,
                    "frameHeight": 8,
                    "scale": 4,
                    "animations": {
                        "idle": [
                            {"x": 0, "y": 0, "durationMs": 100},
                            {"x": 8, "y": 0, "durationMs": 120},
                        ]
                    },
                    "profileSequence": ["idle"],
                }
            ),
            encoding="utf-8",
        )
        return map_path

    def test_build_profile_frames_crops_sequence_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            map_path = self.write_fixture(Path(tmp))

            spec = generate_profile_cat.load_profile_map(map_path)
            frames, durations = generate_profile_cat.build_profile_frames(spec)

        self.assertEqual([frame.size for frame in frames], [(8, 8), (8, 8)])
        self.assertEqual(durations, [100, 120])

    def test_build_profile_frames_rejects_out_of_bounds_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            map_path = self.write_fixture(Path(tmp), frame_count=1)
            data = json.loads(map_path.read_text(encoding="utf-8"))
            data["animations"]["idle"][0]["x"] = 8
            map_path.write_text(json.dumps(data), encoding="utf-8")

            spec = generate_profile_cat.load_profile_map(map_path)
            with self.assertRaisesRegex(ValueError, "outside sprite sheet"):
                generate_profile_cat.build_profile_frames(spec)

    def test_render_profile_banner_keeps_existing_canvas_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            map_path = self.write_fixture(Path(tmp))
            spec = generate_profile_cat.load_profile_map(map_path)
            frames, _ = generate_profile_cat.build_profile_frames(spec)

            banner = generate_profile_cat.render_profile_banner_frame(
                frames[0],
                generate_profile_cat.LIGHT_SCENES[0],
                scale=spec.scale,
            )

        self.assertEqual(banner.size, (generate_profile_cat.WIDTH, generate_profile_cat.HEIGHT))
        self.assertEqual(banner.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
