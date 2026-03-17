#!/usr/bin/env python3
import os
import argparse
import json

def load_config(config_path="config.json"):
    """Load configuration from a JSON file."""
    default_config = {
        "output_file": "Mono.txt",
        "ignored_dirs": [],
        "ignored_files": [],
        "ignored_extensions": [],
        "skip_css_if_no_ext": True
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return {**default_config, **json.load(f)}
        except Exception as e:
            print(f"Error loading config: {e}")
    return default_config

def merge_files(
    directory,
    extension=None,
    recursive=False,
    output_file=None,
    ignore_dirs=None,
    ignore_exts=None
):
    config = load_config()
    
    # Finalize output filename
    out_path = output_file or config.get("output_file", "Mono.txt")

    # Build directory ignore set
    ignore_set = set(config.get("ignored_dirs", []))
    if ignore_dirs:
        for entry in ignore_dirs:
            if entry:
                parts = [p.strip() for p in entry.split(',') if p.strip()]
                ignore_set.update(parts)

    # Build extension ignore set
    ignored_ext_set = set(config.get("ignored_extensions", []))
    if ignore_exts:
        for entry in ignore_exts:
            if entry:
                parts = [p.strip() for p in entry.split(',') if p.strip()]
                for p in parts:
                    ignored_ext_set.add(p if p.startswith('.') else f'.{p}')

    ignored_files = set(config.get("ignored_files", []))
    skip_css = config.get("skip_css_if_no_ext", True)

    if extension and not extension.startswith('.'):
        extension = f'.{extension}'

    with open(out_path, "w", encoding="utf-8") as outfile:
        if recursive:
            for root, dirs, files in os.walk(directory):
                # Prune directories in-place
                dirs[:] = [d for d in dirs if d not in ignore_set]

                norm_parts = os.path.normpath(root).split(os.sep)
                if any(part in ignore_set for part in norm_parts):
                    continue

                for file in files:
                    if file in ignored_files:
                        continue

                    lower = file.lower()
                    if any(lower.endswith(ext) for ext in ignored_ext_set):
                        continue

                    if extension is None and skip_css and lower.endswith('.css'):
                        continue

                    if extension is None or lower.endswith(extension):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, directory)
                        outfile.write(f"----- {rel_path} -----\n")
                        try:
                            with open(file_path, "r", encoding="utf-8") as infile:
                                outfile.write(infile.read())
                        except Exception as e:
                            outfile.write(f"[Error reading file: {e}]\n")
                        outfile.write("\n")
        else:
            for entry in os.listdir(directory):
                if entry in ignored_files or entry in ignore_set:
                    continue

                lower = entry.lower()
                if any(lower.endswith(ext) for ext in ignored_ext_set):
                    continue

                file_path = os.path.join(directory, entry)

                if extension is None and skip_css and lower.endswith('.css'):
                    continue

                if os.path.isfile(file_path) and (extension is None or lower.endswith(extension)):
                    outfile.write(f"----- {entry} -----\n")
                    try:
                        with open(file_path, "r", encoding="utf-8") as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"[Error reading file: {e}]\n")
                    outfile.write("\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Merge all files of a given type from a directory into one 'Mono' file."
    )
    parser.add_argument("directory", help="Directory to scan for files")
    parser.add_argument(
        "extension",
        nargs="?",
        default=None,
        help="Optional file extension to merge."
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively search subdirectories"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Name of the output file (overrides config)"
    )
    parser.add_argument(
        "--ignore-dirs",
        nargs="*",
        default=None,
        help="Extra directories to ignore"
    )
    parser.add_argument(
        "--ignore-exts",
        nargs="*",
        default=None,
        help="Extra file extensions to ignore."
    )

    args = parser.parse_args()
    merge_files(
        args.directory,
        args.extension,
        args.recursive,
        args.output,
        args.ignore_dirs,
        args.ignore_exts
    )