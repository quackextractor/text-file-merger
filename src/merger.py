import os
import shutil
import tempfile
import string
import re
import subprocess
import platform
from src.config import load_config
from src.filters import GitIgnoreFilter, _get_ignore_config, _is_file_included
from src.pdf_utils import convert_to_pdf, PDF_SUPPORT

try:
    import docx
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

try:
    from docx2pdf import convert as convert_docx
    DOCX2PDF_SUPPORT = True
except ImportError:
    DOCX2PDF_SUPPORT = False


def _extract_legacy_doc_binary(file_path):
    """Brute-force extracts printable text from a legacy .doc binary file."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()

        # MS Word often uses UTF-16LE, which looks like 't\x00e\x00x\x00t\x00' in binary.
        # Stripping null bytes helps reveal the hidden text strings.
        cleaned_data = data.replace(b'\x00', b'')

        # Decode to string, ignoring errors for bytes that don't map to characters
        raw_text = cleaned_data.decode('utf-8', errors='ignore')

        # Filter out anything that isn't a standard printable character or whitespace
        printable = set(string.printable)
        filtered_text = ''.join(filter(lambda x: x in printable, raw_text))

        # Clean up the massive gaps of whitespace caused by the stripped binary data
        filtered_text = re.sub(r'\n\s*\n', '\n\n', filtered_text)
        filtered_text = re.sub(r' {2,}', ' ', filtered_text)

        return filtered_text.strip()
    except Exception as e:
        return f"[Failed to extract legacy .doc text: {e}]"


def _merge_recursive(directory, extension, ignore_set, ignored_ext_set, ignored_files, skip_css,
                     cancel_check, dry_run, log_callback, outfile, item_callback=None, git_filter=None,
                     pdf_mode=False, pdf_temp_dir=None, pdf_list=None, styled_pdf=False):
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
                _merge_single_file(outfile, file_path, rel_path, dry_run, log_callback, pdf_mode, pdf_temp_dir, pdf_list, styled_pdf)
                if item_callback:
                    item_callback()


def _merge_flat(directory, extension, ignore_set, ignored_ext_set, ignored_files, skip_css,
                cancel_check, dry_run, log_callback, outfile, item_callback=None, git_filter=None,
                pdf_mode=False, pdf_temp_dir=None, pdf_list=None, styled_pdf=False):
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
            _merge_single_file(outfile, full_path, entry, dry_run, log_callback, pdf_mode, pdf_temp_dir, pdf_list, styled_pdf)
            if item_callback:
                item_callback()


def _merge_single_file(outfile, file_path, display_name, dry_run, log_callback, pdf_mode=False, pdf_temp_dir=None, pdf_list=None, styled_pdf=False):
    if dry_run:
        if log_callback:
            log_callback(f"Would merge: {display_name}")
        return

    is_docx = file_path.lower().endswith('.docx')
    is_doc = file_path.lower().endswith('.doc')

    if pdf_mode:
        try:
            safe_name = display_name.replace(os.sep, "_").replace("/", "_").replace("\\", "_") + ".pdf"
            pdf_path = os.path.join(pdf_temp_dir, safe_name)

            target_txt_path = file_path
            temp_txt = None
            direct_pdf_created = False

            # Tier 1: Try MS Word via docx2pdf
            if is_docx and DOCX2PDF_SUPPORT:
                try:
                    convert_docx(file_path, pdf_path)
                    pdf_list.append(pdf_path)
                    direct_pdf_created = True
                except Exception as e:
                    if log_callback:
                        log_callback(f"MS Word conversion failed: {e}")

            # Tier 2: Try LibreOffice Headless
            if is_docx and not direct_pdf_created:
                try:
                    system = platform.system()
                    if system == "Windows":
                        lo_path = r"C:\Program Files\LibreOffice\program\soffice.exe"
                    elif system == "Darwin":
                        lo_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
                    else:
                        lo_path = "soffice"

                    can_run_lo = True
                    if system in ["Windows", "Darwin"] and not os.path.exists(lo_path):
                        can_run_lo = False

                    if can_run_lo:
                        subprocess.run(
                            [lo_path, "--headless", "--convert-to", "pdf", "--outdir", pdf_temp_dir, file_path],
                            check=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )

                        lo_out_name = os.path.splitext(os.path.basename(file_path))[0] + ".pdf"
                        lo_out_path = os.path.join(pdf_temp_dir, lo_out_name)

                        if os.path.exists(lo_out_path):
                            if lo_out_path != pdf_path:
                                if os.path.exists(pdf_path):
                                    os.remove(pdf_path)
                                os.rename(lo_out_path, pdf_path)
                            pdf_list.append(pdf_path)
                            direct_pdf_created = True
                            if log_callback:
                                log_callback(f"LibreOffice conversion successful: {display_name}")
                except Exception as e:
                    if log_callback:
                        log_callback(f"LibreOffice conversion failed: {e}")

            # Tier 3: Fallback to Plain Text Extraction
            if not direct_pdf_created:
                if is_docx and DOCX_SUPPORT:
                    doc = docx.Document(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    temp_txt = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
                    temp_txt.write(text)
                    temp_txt.close()
                    target_txt_path = temp_txt.name

                elif is_doc:
                    text = _extract_legacy_doc_binary(file_path)
                    temp_txt = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8')
                    temp_txt.write(text)
                    temp_txt.close()
                    target_txt_path = temp_txt.name

                convert_to_pdf(target_txt_path, pdf_path, display_name, styled_pdf)
                pdf_list.append(pdf_path)

            if temp_txt:
                os.remove(temp_txt.name)

            if log_callback and not direct_pdf_created:
                log_callback(f"Prepared PDF via text fallback: {display_name}")

        except Exception as e:
            if log_callback:
                log_callback(f"Error compiling {display_name}: {e}")
    else:
        outfile.write(f"----- {display_name} -----\n")
        try:
            if is_docx and DOCX_SUPPORT:
                doc = docx.Document(file_path)
                outfile.write("\n".join([para.text for para in doc.paragraphs]))
            elif is_doc:
                outfile.write(_extract_legacy_doc_binary(file_path))
            else:
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
    keep_pdf_sources=False,
    styled_pdf=False
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
                             pdf_mode, pdf_temp_dir, pdf_list, styled_pdf)
        else:
            _merge_flat(directory, extension, ignore_set, ignored_ext_set, ignored_files,
                        skip_css, cancel_check, dry_run, log_callback, outfile, item_callback, git_filter,
                        pdf_mode, pdf_temp_dir, pdf_list, styled_pdf)

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
