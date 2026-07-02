from dataclasses import dataclass
from typing import List, Optional, Set
import os


@dataclass
class FileTask:
    index: int              # deterministic order
    path: str               # absolute path
    display_name: str       # rel path from source directory
    size: int               # file size in bytes
    kind: str               # 'text', 'docx', 'doc', 'other_text'


def collect_files(
    directory: str,
    extension: Optional[str],
    recursive: bool,
    ignore_set: Set[str],
    ignored_ext_tuple: tuple,
    ignored_files: Set[str],
    skip_css: bool,
    git_filter=None,
    include_list: Optional[List[str]] = None
) -> List[FileTask]:
    directory = os.path.abspath(directory)
    tasks = []
    index = 0

    if extension and not extension.startswith('.'):
        extension = f'.{extension}'

    if recursive:
        for root, dirs, files in os.walk(directory):
            # Sort directories and files to ensure deterministic traversal order
            dirs.sort()
            files.sort()

            # Prune directories based on ignore_set and git_filter
            if git_filter:
                dirs[:] = [d for d in dirs if not git_filter.is_ignored(os.path.join(root, d), is_dir=True)]
            dirs[:] = [d for d in dirs if d not in ignore_set]

            for file in files:
                file_path = os.path.join(root, file)
                display_name = os.path.relpath(file_path, directory).replace(os.sep, '/')

                # 1. Apply Selective Include Filter
                if include_list is not None and display_name not in include_list:
                    continue

                # 2. Apply Ignore Rules
                if git_filter and git_filter.is_ignored(file_path, is_dir=False):
                    continue

                if file in ignored_files:
                    continue

                lower_name = file.lower()
                if lower_name.endswith(ignored_ext_tuple):
                    continue

                if extension is None and skip_css and lower_name.endswith('.css'):
                    continue

                if extension is not None and not lower_name.endswith(extension):
                    continue

                # Classify the file type
                if lower_name.endswith('.docx'):
                    kind = 'docx'
                elif lower_name.endswith('.doc'):
                    kind = 'doc'
                elif lower_name.endswith('.txt'):
                    kind = 'text'
                else:
                    kind = 'other_text'

                try:
                    size = os.path.getsize(file_path)
                except OSError:
                    size = 0

                tasks.append(FileTask(
                    index=index,
                    path=file_path,
                    display_name=display_name,
                    size=size,
                    kind=kind
                ))
                index += 1
    else:
        try:
            entries = os.listdir(directory)
        except OSError:
            return []

        # Sort entries to ensure deterministic order
        entries.sort()

        for entry in entries:
            full_path = os.path.join(directory, entry)
            if not os.path.isfile(full_path):
                continue

            display_name = entry.replace(os.sep, '/')

            # 1. Apply Selective Include Filter
            if include_list is not None and display_name not in include_list:
                continue

            # 2. Apply Ignore Rules
            if entry in ignore_set:
                continue

            if git_filter and git_filter.is_ignored(full_path, is_dir=False):
                continue

            if entry in ignored_files:
                continue

            lower_name = entry.lower()
            if lower_name.endswith(ignored_ext_tuple):
                continue

            if extension is None and skip_css and lower_name.endswith('.css'):
                continue

            if extension is not None and not lower_name.endswith(extension):
                continue

            # Classify the file type
            if lower_name.endswith('.docx'):
                kind = 'docx'
            elif lower_name.endswith('.doc'):
                kind = 'doc'
            elif lower_name.endswith('.txt'):
                kind = 'text'
            else:
                kind = 'other_text'

            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0

            tasks.append(FileTask(
                index=index,
                path=full_path,
                display_name=display_name,
                size=size,
                kind=kind
            ))
            index += 1

    return tasks
