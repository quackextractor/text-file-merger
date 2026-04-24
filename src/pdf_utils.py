import os
import textwrap

try:
    from fpdf import FPDF
    from pypdf import PdfWriter
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


def convert_to_pdf(txt_path, pdf_path, display_name):
    if not PDF_SUPPORT:
        raise ImportError("fpdf2 and pypdf are required for generation")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=8)

    pdf.cell(0, 5, text=f"File: {display_name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, text="", new_x="LMARGIN", new_y="NEXT")

    wrapper = textwrap.TextWrapper(width=95, replace_whitespace=False, drop_whitespace=False, break_long_words=True)

    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            safe_line = line.rstrip('\n').replace('\t', '    ').encode("latin1", "replace").decode("latin1")
            if not safe_line:
                pdf.cell(0, 5, text="", new_x="LMARGIN", new_y="NEXT")
                continue

            wrapped_lines = wrapper.wrap(safe_line)
            for w_line in wrapped_lines:
                pdf.cell(0, 5, text=w_line, new_x="LMARGIN", new_y="NEXT")

    pdf.output(pdf_path)
