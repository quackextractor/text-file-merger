import os
import sys
import textwrap

try:
    from fpdf import FPDF
    from pypdf import PdfWriter
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


def _get_system_font():
    """Attempts to locate a standard monospaced Unicode TTF font based on the OS."""
    if sys.platform == "win32":
        return "C:\\Windows\\Fonts\\cour.ttf"  # Courier New
    elif sys.platform == "darwin":
        return "/Library/Fonts/Courier New.ttf"
    else:
        # Common Linux font paths
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/usr/share/fonts/truetype/freefont/FreeMono.ttf"
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return None


def convert_to_pdf(txt_path, pdf_path, display_name, styled=False):
    if not PDF_SUPPORT:
        raise ImportError("fpdf2 and pypdf are required for generation")

    pdf = FPDF()
    pdf.add_page()

    if styled:
        pdf.set_font("Helvetica", style="B", size=14)
        safe_title = f"File: {display_name}".encode("latin1", "replace").decode("latin1")
        pdf.cell(0, 8, text=safe_title, new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, text="", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=10)
        use_unicode = False
    else:
        # Attempt to load a Unicode-compatible system font
        font_path = _get_system_font()
        use_unicode = False

        if font_path and os.path.exists(font_path):
            try:
                pdf.add_font("SysFont", style="", fname=font_path)
                pdf.set_font("SysFont", size=8)
                use_unicode = True
            except Exception:
                pdf.set_font("Courier", size=8)
        else:
            pdf.set_font("Courier", size=8)

        # Fallback text cleaner if a Unicode font isn't available
        def sanitize(text):
            if use_unicode:
                return text
            return text.encode("latin1", "replace").decode("latin1")

        safe_title = sanitize(f"File: {display_name}")
        pdf.cell(0, 5, text=safe_title, new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, text="", new_x="LMARGIN", new_y="NEXT")

    # TextWrapper keeps long lines from running off the page
    wrapper = textwrap.TextWrapper(width=100 if styled else 95, replace_whitespace=False, drop_whitespace=False, break_long_words=True)

    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if styled:
                safe_line = line.rstrip('\n').replace('\t', '    ').encode("latin1", "replace").decode("latin1")
            else:
                safe_line = sanitize(line.rstrip('\n').replace('\t', '    '))

            if not safe_line:
                pdf.cell(0, 5, text="", new_x="LMARGIN", new_y="NEXT")
                continue

            wrapped_lines = wrapper.wrap(safe_line)
            for w_line in wrapped_lines:
                pdf.cell(0, 5 if styled else 4, text=w_line, new_x="LMARGIN", new_y="NEXT")

    pdf.output(pdf_path)


def _convert_text_to_pdf_worker(args):
    txt_path, pdf_path, display_name, styled_pdf = args
    convert_to_pdf(txt_path, pdf_path, display_name, styled_pdf)
    return pdf_path


def _merge_pdf_files(pdf_list, out_path, pdf_batch_threshold=200, log_callback=None):
    import tempfile

    if len(pdf_list) <= pdf_batch_threshold:
        merger = PdfWriter()
        for p in pdf_list:
            merger.append(p)
        merger.write(out_path)
        merger.close()
    else:
        if log_callback:
            log_callback(f"Merging {len(pdf_list)} PDFs in batches of 50...")
        chunk_size = 50
        batch_files = []

        for i in range(0, len(pdf_list), chunk_size):
            chunk = pdf_list[i: i + chunk_size]
            chunk_merger = PdfWriter()
            for p in chunk:
                chunk_merger.append(p)

            temp_batch = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_batch.close()

            chunk_merger.write(temp_batch.name)
            chunk_merger.close()
            batch_files.append(temp_batch.name)

        final_merger = PdfWriter()
        for b in batch_files:
            final_merger.append(b)
        final_merger.write(out_path)
        final_merger.close()

        for b in batch_files:
            try:
                os.remove(b)
            except Exception:
                pass
