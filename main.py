#!/usr/bin/env python3
import argparse
import customtkinter as ctk
from src.gui import MergeApp
from src.merger import merge_files

try:
    from tkinterdnd2 import TkinterDnD
except ImportError:
    TkinterDnD = None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Merge files via CLI or GUI.")
    parser.add_argument("directory", nargs="?", help="Directory to scan")
    parser.add_argument("extension", nargs="?", default=None)
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--gui", action="store_true", help="Force GUI mode")
    parser.add_argument("--no-gitignore", action="store_true", help="Disable auto reading of .gitignore files")
    parser.add_argument("--pdf", action="store_true", help="Merge into a single PDF")
    parser.add_argument("--keep-sources", action="store_true", help="Keep individual source PDFs when merging into a single PDF")
    parser.add_argument("--keep-sources-txt", action="store_true", help="Keep individual source text files when merging")
    parser.add_argument("--styled-pdf", action="store_true", help="Apply styling to the output PDF")

    args, unknown = parser.parse_known_args()

    if args.gui or not args.directory:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        if TkinterDnD:
            root = TkinterDnD.Tk()
            is_dark = ctk.get_appearance_mode() == "Dark"
            bg_color = ctk.ThemeManager.theme["CTk"]["fg_color"][1 if is_dark else 0]
            root.configure(bg=bg_color, highlightthickness=0)

            if is_dark:
                try:
                    import ctypes
                    root.update()
                    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
                    rendering_policy = 20
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, rendering_policy, ctypes.byref(ctypes.c_int(1)), 4
                    )
                except Exception:
                    pass
        else:
            root = ctk.CTk()

        app = MergeApp(root)
        root.mainloop()
    else:
        merge_files(
            args.directory,
            config=None,
            extension=args.extension,
            recursive=args.recursive,
            output_file=args.output,
            use_gitignore=not args.no_gitignore,
            pdf_mode=args.pdf,
            keep_pdf_sources=args.keep_sources,
            keep_txt_sources=args.keep_sources_txt,
            styled_pdf=args.styled_pdf
        )
