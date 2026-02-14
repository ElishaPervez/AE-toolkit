import json
import unittest
from unittest.mock import mock_open, patch

from amv import config as config_module


class ConfigMigrationTests(unittest.TestCase):
    def test_normalize_config_migrates_legacy_keys_and_coerces_mode_flags(self):
        raw_config = {
            "recent_files": ["a.wav", "a.wav", "", 123, "b.wav"],
            "max_recent": 2,
            "force_cpu": True,
            "setup_type": "gpu",
            "enabled": False,
            "fp16": False,
            "fp8": False,
            "batch_size": 1,
        }

        normalized = config_module._normalize_config(raw_config)

        self.assertEqual(set(normalized.keys()), set(config_module.DEFAULT_CONFIG.keys()))
        self.assertEqual(normalized["recent_files"], ["a.wav", "b.wav"])
        self.assertEqual(normalized["max_recent"], 2)
        self.assertEqual(normalized["setup_type"], "gpu")
        self.assertFalse(normalized["force_cpu"])

    def test_load_config_saves_migrated_schema_when_legacy_keys_exist(self):
        raw_config = {
            "recent_files": ["x.wav", "x.wav", "y.wav"],
            "max_recent": 2,
            "setup_type": "cpu",
            "force_cpu": False,
            "enabled": True,
        }
        mocked_open = mock_open(read_data=json.dumps(raw_config))

        with patch("amv.config.os.path.exists", return_value=True), \
                patch("amv.config.open", mocked_open, create=True), \
                patch.object(config_module, "save_config") as save_mock:
            loaded = config_module.load_config()

        self.assertEqual(set(loaded.keys()), set(config_module.DEFAULT_CONFIG.keys()))
        self.assertEqual(loaded["recent_files"], ["x.wav", "y.wav"])
        self.assertEqual(loaded["max_recent"], 2)
        save_mock.assert_called_once_with(loaded)

    def test_save_config_normalizes_and_clamps_values(self):
        dirty_config = {
            "recent_files": ["x.wav", "", "x.wav", "y.wav"],
            "max_recent": 0,
            "setup_type": "cpu",
            "force_cpu": False,
            "enabled": True,
        }

        with patch("amv.config.open", mock_open(), create=True), \
                patch("amv.config.json.dump") as dump_mock:
            config_module.save_config(dirty_config)

        persisted = dump_mock.call_args.args[0]
        self.assertEqual(set(persisted.keys()), set(config_module.DEFAULT_CONFIG.keys()))
        self.assertEqual(persisted["max_recent"], 1)
        self.assertEqual(persisted["recent_files"], ["x.wav"])
        self.assertEqual(persisted["setup_type"], "cpu")
        self.assertFalse(persisted["force_cpu"])


if __name__ == "__main__":
    unittest.main()
