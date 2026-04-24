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


def convert_to_pdf(txt_path, pdf_path, display_name):
    if not PDF_SUPPORT:
        raise ImportError("fpdf2 and pypdf are required for generation")

    pdf = FPDF()
    pdf.add_page()

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
    wrapper = textwrap.TextWrapper(width=95, replace_whitespace=False, drop_whitespace=False, break_long_words=True)

    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            safe_line = sanitize(line.rstrip('\n').replace('\t', '    '))

            if not safe_line:
                pdf.cell(0, 5, text="", new_x="LMARGIN", new_y="NEXT")
                continue

            wrapped_lines = wrapper.wrap(safe_line)
            for w_line in wrapped_lines:
                pdf.cell(0, 5, text=w_line, new_x="LMARGIN", new_y="NEXT")

    pdf.output(pdf_path)
