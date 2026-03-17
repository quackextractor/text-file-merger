#!/usr/bin/env python3
import os
import argparse

def merge_files(
    directory,
    extension=None,
    recursive=False,
    output_file="Mono.txt",
    ignore_dirs=None,
    ignore_exts=None
):
    """
    Merge files from directory into one file. Each file's content is preceded by
    a header containing its relative path.

    Default behavior:
    - Always ignores 'node_modules' and 'dist' directories (can be extended via --ignore-dirs).
    - Always ignores 'package-lock.json' files.
    - When no extension filter is provided, .css files are skipped by default.
    - Added: Hardcoded extension ignore list for common binary formats.
    """

    default_ignored_dirs = {
        'node_modules', 'dist', 'storage', '.idea',
        '.git', '__pycache__', '.venv', 'bin', 'obj', 'Debug', '.next'
    }

    if ignore_dirs:
        extra = []
        for entry in ignore_dirs:
            if not entry:
                continue
            parts = [p.strip() for p in entry.split(',') if p.strip()]
            extra.extend(parts)
        ignore_set = default_ignored_dirs.union(set(extra))
    else:
        ignore_set = default_ignored_dirs

    if extension and not extension.startswith('.'):
        extension = f'.{extension}'

    ignored_files = {'package-lock.json'}

    # Hardcoded ignored extensions for stuff that cannot be merged as text
    default_ignored_exts = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp',
        '.ico', '.tiff', '.mp4', '.mp3', '.wav', '.ogg',
        '.pdf', '.zip', '.tar', '.gz', '.rar', '.svg', '.log', '.sln'
    }

    if ignore_exts:
        extra_exts = []
        for entry in ignore_exts:
            if not entry:
                continue
            parts = [p.strip() for p in entry.split(',') if p.strip()]
            extra_exts.extend(parts)
        extra_exts = {e if e.startswith('.') else f'.{e}' for e in extra_exts}
        ignored_ext_set = default_ignored_exts.union(extra_exts)
    else:
        ignored_ext_set = default_ignored_exts

    with open(output_file, "w", encoding="utf-8") as outfile:
        if recursive:
            for root, dirs, files in os.walk(directory):
                for d in list(dirs):
                    if d in ignore_set:
                        dirs.remove(d)

                norm_parts = os.path.normpath(root).split(os.sep)
                if any(part in ignore_set for part in norm_parts):
                    continue

                for file in files:
                    if file in ignored_files:
                        continue

                    lower = file.lower()
                    if any(lower.endswith(ext) for ext in ignored_ext_set):
                        continue

                    if extension is None and lower.endswith('.css'):
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

                if extension is None and lower.endswith('.css'):
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
        help="Optional file extension to merge. When omitted .css files are skipped."
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Recursively search subdirectories"
    )
    parser.add_argument(
        "-o", "--output",
        default="Mono.txt",
        help="Name of the output file"
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
        help="Extra file extensions to ignore. Supports comma separated entries."
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