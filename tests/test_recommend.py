from __future__ import annotations

import unittest

from openlocal.recommend import ProfileError, load_profiles, recommend, validate_profile


def snapshot(vram_gb: float, ram_gb: float = 64) -> dict:
    return {
        "gpu": {
            "vendor": "nvidia",
            "count": 1,
            "devices": [{"model": "Test GPU", "vram_gb": vram_gb}],
        },
        "ram_gb": ram_gb,
        "runtime_path": "docker-linux",
    }


class ProfileTests(unittest.TestCase):
    def test_repository_profiles_are_valid_and_unique(self):
        profiles = load_profiles()
        self.assertGreaterEqual(len(profiles), 5)
        self.assertEqual(len({profile["id"] for profile in profiles}), len(profiles))

    def test_validation_reports_missing_sections(self):
        with self.assertRaisesRegex(ProfileError, "hardware"):
            validate_profile({"schema_version": 1, "id": "broken"})


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.profiles = load_profiles()

    def test_24gb_returns_fast_balanced_and_max_quality(self):
        results = recommend(snapshot(24), self.profiles)
        self.assertEqual([item.category for item in results], ["FAST", "BALANCED", "MAX QUALITY"])
        self.assertEqual(
            [item.profile["model"]["parameters_b"] for item in results],
            [8, 14, 32],
        )

    def test_8gb_stays_within_vram_and_ram(self):
        results = recommend(snapshot(8, 16), self.profiles)
        self.assertTrue(results)
        self.assertTrue(all(item.profile["estimates"]["vram_gb"] <= 8 for item in results))
        self.assertTrue(all(item.profile["hardware"]["min_ram_gb"] <= 16 for item in results))

    def test_no_gpu_has_no_recommendation(self):
        result = recommend({"gpu": {"vendor": None, "count": 0, "devices": []}, "ram_gb": 64}, self.profiles)
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
