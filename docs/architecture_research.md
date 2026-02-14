# Architecture Notes: Hybrid CPU/GPU Execution

The toolkit supports both CPU-only and NVIDIA GPU execution modes.

## Runtime Behavior
- Hardware is detected on launch.
- GPU mode uses CUDA PyTorch with BS-Roformer (FP16 when supported).
- CPU mode uses Kim Vocal 2 (ONNX) with CPUExecutionProvider.

## Switching Modes
- Open `Settings -> System Check` (Setup screen).
- Use `Switch Dependencies` to install/switch CPU or GPU dependency sets.
- The selected mode is persisted in `config.json` (`setup_type` + `force_cpu`).
