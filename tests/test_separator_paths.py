import unittest
from unittest.mock import patch

from amv.separator import _build_output_name, _get_unique_path


class SeparatorPathTests(unittest.TestCase):
    def test_build_output_name_uses_generated_extension(self):
        self.assertEqual(
            _build_output_name("track", "[vocals]", "track_vocals.wav"),
            "track [vocals].wav",
        )
        self.assertEqual(
            _build_output_name("track", "[instrumental]", "track_inst.flac"),
            "track [instrumental].flac",
        )

    def test_build_output_name_defaults_to_wav_without_extension(self):
        self.assertEqual(
            _build_output_name("track", "[vocals]", "track_vocals"),
            "track [vocals].wav",
        )

    def test_get_unique_path_returns_original_when_available(self):
        target = r"C:\media\song [vocals].wav"
        with patch("amv.separator.os.path.exists", return_value=False):
            self.assertEqual(_get_unique_path(target), target)

    def test_get_unique_path_appends_incrementing_suffix(self):
        target = r"C:\media\song [vocals].wav"
        collisions = {
            target: True,
            r"C:\media\song [vocals] (1).wav": True,
            r"C:\media\song [vocals] (2).wav": False,
        }

        with patch("amv.separator.os.path.exists", side_effect=lambda p: collisions.get(p, False)):
            self.assertEqual(
                _get_unique_path(target),
                r"C:\media\song [vocals] (2).wav",
            )


if __name__ == "__main__":
    unittest.main()
