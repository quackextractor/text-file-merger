import os
import sys
import json


def get_bundled_config():
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(os.path.dirname(__file__))

    bundled_config_path = os.path.join(base_path, "config.json")

    if os.path.exists(bundled_config_path):
        try:
            with open(bundled_config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading bundled config: {e}")

    return {
        "output_file": "Mono.txt",
        "output_dir": "out",
        "ignored_dirs": [
            "node_modules", "dist", "storage", ".idea", ".git",
            "__pycache__", ".venv", "bin", "obj", "Debug", ".next"
        ],
        "ignored_files": [
            "package-lock.json"
        ],
        "ignored_extensions": [
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp",
            ".ico", ".tiff", ".mp4", ".mp3", ".wav", ".ogg",
            ".pdf", ".zip", ".tar", ".gz", ".rar", ".svg",
            ".log", ".sln"
        ],
        "use_gitignore": True,
        "include_tree": True,
        "tree_ignore_level": "none",
        "performance": {
            "max_workers": 0,
            "large_file_threshold_mb": 5,
            "output_buffer_kb": 256,
            "progress_update_interval_ms": 100,
            "batch_libreoffice": True,
            "parallel_pdf_fallback": True,
            "min_tasks_for_parallel": 8,
            "pdf_batch_threshold": 200
        }
    }


DEFAULT_CONFIG = get_bundled_config()


def load_config(config_path="config.json"):
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                perf = {**DEFAULT_CONFIG.get("performance", {}), **loaded.get("performance", {})}
                config = {**DEFAULT_CONFIG, **loaded}
                config["performance"] = perf
                return config
        except Exception as e:
            print(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()
