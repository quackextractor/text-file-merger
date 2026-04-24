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
        "skip_css_if_no_ext": True,
        "use_gitignore": True
    }


DEFAULT_CONFIG = get_bundled_config()


def load_config(config_path="config.json"):
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception as e:
            print(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()
