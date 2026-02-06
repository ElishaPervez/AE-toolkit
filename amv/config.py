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
    "force_cpu": False
}

def load_config():
    """Load configuration from JSON. Creates default config if none exists."""
    if not os.path.exists(CONFIG_FILE):
        config = DEFAULT_CONFIG.copy()
        save_config(config)
        return config
    try:
        with open(CONFIG_FILE, 'r') as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"Could not load config, using defaults: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to JSON."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

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
    "Kim_Vocal_2.onnx": "Kim Vocal 2 (Anime/High Pitch - Improved)"
}
