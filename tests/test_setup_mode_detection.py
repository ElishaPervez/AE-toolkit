import unittest
from unittest.mock import patch

from amv.screens.setup import SetupScreen
from amv.screens import settings as settings_screen


class SetupModeDetectionTests(unittest.TestCase):
    def test_cpu_switch_skips_reinstall_when_cpu_torch_installed_but_config_is_gpu(self):
        screen = SetupScreen(target_mode="cpu")

        with patch("amv.screens.setup.load_config", return_value={"setup_type": "gpu"}), \
             patch("amv.screens.setup.get_torch_status", return_value=(True, "2.10.0+cpu")), \
             patch("amv.screens.setup.verify_cuda_torch", return_value=False):
            results = screen._collect_cpu_switch()

        self.assertEqual(results["issues"], [])
        self.assertEqual(results["installs"], [])
        self.assertEqual(results["success_mode"], "cpu")

    def test_cpu_switch_requires_install_when_torch_missing(self):
        screen = SetupScreen(target_mode="cpu")

        with patch("amv.screens.setup.load_config", return_value={"setup_type": "cpu"}), \
             patch("amv.screens.setup.get_torch_status", return_value=(False, None)), \
             patch("amv.screens.setup.verify_cuda_torch", return_value=False):
            results = screen._collect_cpu_switch()

        self.assertIsNone(results["success_mode"])
        self.assertGreater(len(results["issues"]), 0)
        self.assertGreater(len(results["installs"]), 0)

    def test_gpu_switch_skips_reinstall_when_cuda_torch_installed_but_config_is_cpu(self):
        screen = SetupScreen(target_mode="gpu")

        with patch("amv.screens.setup.load_config", return_value={"setup_type": "cpu"}), \
             patch("amv.screens.setup.verify_cuda_torch", return_value=True), \
             patch("amv.screens.setup.check_nvidia_gpu", return_value="NVIDIA GeForce RTX 5060 Ti"):
            results = screen._collect_gpu_switch()

        self.assertEqual(results["issues"], [])
        self.assertEqual(results["installs"], [])
        self.assertEqual(results["success_mode"], "gpu")

    def test_settings_effective_mode_uses_installed_torch_not_config(self):
        with patch("amv.screens.settings.get_torch_status", return_value=(True, "2.10.0+cpu")), \
             patch("amv.screens.settings.verify_cuda_torch", return_value=False):
            mode = settings_screen.get_effective_mode()

        self.assertEqual(mode, "cpu")


if __name__ == "__main__":
    unittest.main()
