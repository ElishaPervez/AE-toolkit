# ═══════════════════════════════════════════════════════════════════════════════
# AMV Toolkit - Configuration
# ═══════════════════════════════════════════════════════════════════════════════

import os
import json
import logging

# Paths
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(SCRIPT_DIR, "models")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

# Ensure models directory exists
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR)

# Default Config
DEFAULT_CONFIG = {
    "recent_files": [],
    "max_recent": 10,
    "force_cpu": False,
    "setup_type": "cpu"
}

def _normalize_config(config):
    """Return a schema-valid config and strip stale keys from older versions."""
    if not isinstance(config, dict):
        return DEFAULT_CONFIG.copy()

    normalized = DEFAULT_CONFIG.copy()

    # recent_files: list[str], de-duplicated in order, trimmed by max_recent
    recent_files = config.get("recent_files", [])
    if isinstance(recent_files, list):
        cleaned = []
        seen = set()
        for item in recent_files:
            if not isinstance(item, str):
                continue
            item = item.strip()
            if not item or item in seen:
                continue
            seen.add(item)
            cleaned.append(item)
        normalized["recent_files"] = cleaned

    max_recent = config.get("max_recent", DEFAULT_CONFIG["max_recent"])
    if isinstance(max_recent, int):
        normalized["max_recent"] = max(1, min(50, max_recent))

    normalized["force_cpu"] = bool(config.get("force_cpu", DEFAULT_CONFIG["force_cpu"]))

    setup_type = config.get("setup_type", DEFAULT_CONFIG["setup_type"])
    if isinstance(setup_type, str) and setup_type.lower() in {"cpu", "gpu"}:
        normalized["setup_type"] = setup_type.lower()

    # Keep mode flags coherent.
    if normalized["setup_type"] == "gpu":
        normalized["force_cpu"] = False
    elif normalized["force_cpu"]:
        normalized["setup_type"] = "cpu"

    normalized["recent_files"] = normalized["recent_files"][:normalized["max_recent"]]
    return normalized

def load_config():
    """Load configuration from JSON. Creates default config if none exists."""
    if not os.path.exists(CONFIG_FILE):
        config = DEFAULT_CONFIG.copy()
        save_config(config)
        return config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        config = _normalize_config(raw)

        # Auto-migrate stale keys/values to the active schema.
        if config != raw:
            save_config(config)
        return config
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Could not load config, using defaults: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to JSON."""
    normalized = _normalize_config(config)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, indent=4)

def get_recent_files():
    """Get list of recent files."""
    return load_config().get("recent_files", [])

def add_recent_file(path):
    """Add a file to recent files list."""
    config = load_config()
    recents = config.get("recent_files", [])
    
    # Remove existing to move to top
    if path in recents:
        recents.remove(path)
    
    recents.insert(0, path)
    
    # Trim
    max_count = config.get("max_recent", 10)
    config["recent_files"] = recents[:max_count]
    save_config(config)

def get_output_dirs():
    """Get output directories based on the directory where user ran the command."""
    # Use original directory where user ran the command, not where script lives
    original_dir = os.environ.get('AMV_ORIGINAL_DIR', os.getcwd())
    base_dir = os.path.join(original_dir, "amv-script")
    return {
        "base": base_dir,
        "video": os.path.join(base_dir, "video downloads"),
        "audio": os.path.join(base_dir, "audio downloads"),
    }

def ensure_output_dirs():
    """Create output directories if they don't exist."""
    dirs = get_output_dirs()
    for path in dirs.values():
        if not os.path.exists(path):
            os.makedirs(path)
    return dirs

# Known AI models for display names
KNOWN_MODELS = {
    "Kim_Vocal_2.onnx": "Kim Vocal 2 (Anime/High Pitch - Improved)",
    "model_bs_roformer_ep_317_sdr_12.9755.ckpt": "BS-Roformer (Best Quality)"
}
