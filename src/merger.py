import os
import shutil
from src.config import load_config
from src.filters import GitIgnoreFilter, _get_ignore_config, _is_file_included
from src.pdf_utils import convert_to_pdf, PDF_SUPPORT


def _merge_recursive(directory, extension, ignore_set, ignored_ext_set, ignored_files, skip_css,
                     cancel_check, dry_run, log_callback, outfile, item_callback=None, git_filter=None,
                     pdf_mode=False, pdf_temp_dir=None, pdf_list=None):
    for root, dirs, files in os.walk(directory):
        if cancel_check and cancel_check():
            break

        if git_filter:
            dirs[:] = [d for d in dirs if not git_filter.is_ignored(os.path.join(root, d), is_dir=True)]

        dirs[:] = [d for d in dirs if d not in ignore_set]
        for file in files:
            if cancel_check and cancel_check():
                break

            file_path = os.path.join(root, file)
            if git_filter and git_filter.is_ignored(file_path, is_dir=False):
                continue

            if _is_file_included(file, root, directory, extension, ignore_set,
                                 ignored_ext_set, ignored_files, skip_css):
                rel_path = os.path.relpath(file_path, directory)
                _merge_single_file(outfile, file_path, rel_path, dry_run, log_callback, pdf_mode, pdf_temp_dir, pdf_list)
                if item_callback:
                    item_callback()


def _merge_flat(directory, extension, ignore_set, ignored_ext_set, ignored_files, skip_css,
                cancel_check, dry_run, log_callback, outfile, item_callback=None, git_filter=None,
                pdf_mode=False, pdf_temp_dir=None, pdf_list=None):
    for entry in os.listdir(directory):
        if cancel_check and cancel_check():
            break

        if entry in ignore_set:
            continue

        full_path = os.path.join(directory, entry)
        if not os.path.isfile(full_path):
            continue

        if git_filter and git_filter.is_ignored(full_path, is_dir=False):
            continue

        if _is_file_included(entry, directory, directory, extension, ignore_set,
                             ignored_ext_set, ignored_files, skip_css):
            _merge_single_file(outfile, full_path, entry, dry_run, log_callback, pdf_mode, pdf_temp_dir, pdf_list)
            if item_callback:
                item_callback()


def _merge_single_file(outfile, file_path, display_name, dry_run, log_callback, pdf_mode=False, pdf_temp_dir=None, pdf_list=None):
    if dry_run:
        if log_callback:
            log_callback(f"Would merge: {display_name}")
        return

    if pdf_mode:
        try:
            safe_name = display_name.replace(os.sep, "_").replace("/", "_").replace("\\", "_") + ".pdf"
            pdf_path = os.path.join(pdf_temp_dir, safe_name)
            convert_to_pdf(file_path, pdf_path, display_name)
            pdf_list.append(pdf_path)
            if log_callback:
                log_callback(f"Prepared PDF: {display_name}")
        except Exception as e:
            if log_callback:
                log_callback(f"Error compiling {display_name}: {e}")
    else:
        outfile.write(f"----- {display_name} -----\n")
        try:
            with open(file_path, "r", encoding="utf-8") as infile:
                outfile.write(infile.read())
            if log_callback:
                log_callback(f"Merged: {display_name}")
        except Exception as e:
            outfile.write(f"[Error reading file: {e}]\n")
            if log_callback:
                log_callback(f"Error reading {display_name}: {e}")
        outfile.write("\n")


def merge_files(
    directory,
    config=None,
    extension=None,
    recursive=False,
    output_file=None,
    ignore_dirs=None,
    ignore_exts=None,
    cancel_check=None,
    dry_run=False,
    log_callback=None,
    item_callback=None,
    use_gitignore=True,
    pdf_mode=False,
    keep_pdf_sources=False
):
    if config is None:
        config = load_config()

    raw_out_path = output_file or config.get("output_file", "Mono.txt")
    out_dir = config.get("output_dir", "out")
    out_path = os.path.join(out_dir, os.path.basename(raw_out_path))

    ignore_set, ignored_ext_set, ignored_files = _get_ignore_config(config, ignore_dirs, ignore_exts)
    skip_css = config.get("skip_css_if_no_ext", True)
    git_filter = GitIgnoreFilter(directory) if use_gitignore else None

    if extension and not extension.startswith('.'):
        extension = f'.{extension}'

    if pdf_mode:
        base, _ = os.path.splitext(out_path)
        out_path = base + ".pdf"

    pdf_temp_dir = None
    pdf_list = []
    if pdf_mode and not dry_run:
        base_filename = os.path.splitext(os.path.basename(out_path))[0]
        pdf_temp_dir = os.path.join(out_dir, base_filename)
        os.makedirs(pdf_temp_dir, exist_ok=True)

    outfile = None
    try:
        if not dry_run and not pdf_mode:
            os.makedirs(out_dir, exist_ok=True)
            outfile = open(out_path, "w", encoding="utf-8")

        if recursive:
            _merge_recursive(directory, extension, ignore_set, ignored_ext_set, ignored_files,
                             skip_css, cancel_check, dry_run, log_callback, outfile, item_callback, git_filter,
                             pdf_mode, pdf_temp_dir, pdf_list)
        else:
            _merge_flat(directory, extension, ignore_set, ignored_ext_set, ignored_files,
                        skip_css, cancel_check, dry_run, log_callback, outfile, item_callback, git_filter,
                        pdf_mode, pdf_temp_dir, pdf_list)

        if pdf_mode and not dry_run and pdf_list:
            if log_callback:
                log_callback("Compiling final PDF structure...")
            try:
                from pypdf import PdfWriter
                merger = PdfWriter()
                for p in pdf_list:
                    merger.append(p)
                merger.write(out_path)
                merger.close()

                if not keep_pdf_sources:
                    shutil.rmtree(pdf_temp_dir)
                    if log_callback:
                        log_callback("Source files cleaned up completely.")
                else:
                    if log_callback:
                        log_callback(f"Source files preserved in: {pdf_temp_dir}")

            except Exception as e:
                if log_callback:
                    log_callback(f"Failed to join sources: {e}")

    finally:
        if outfile:
            outfile.close()

    return out_path
