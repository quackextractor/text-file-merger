#!/usr/bin/env python3
import sys
import os
import fnmatch
import argparse
import json
import threading
import tkinter as tk
import subprocess
import shutil
import textwrap
from tkinter import filedialog
import customtkinter as ctk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None

try:
    from fpdf import FPDF
    from pypdf import PdfWriter
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False


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


class GitIgnoreFilter:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.rules_cache = {}

    def _load_rules(self, directory):
        if directory in self.rules_cache:
            return self.rules_cache[directory]

        rules = []
        gitignore_path = os.path.join(directory, '.gitignore')
        if os.path.exists(gitignore_path):
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            rules.append(line)
            except Exception:
                pass
        self.rules_cache[directory] = rules
        return rules

    def is_ignored(self, file_or_dir_path, is_dir):
        rel_path = os.path.relpath(file_or_dir_path, self.base_dir)
        if rel_path == '.':
            return False

        current_dir = file_or_dir_path if is_dir else os.path.dirname(file_or_dir_path)

        chain = []
        tmp = current_dir
        while True:
            chain.insert(0, tmp)
            if tmp == self.base_dir or tmp == os.path.dirname(tmp):
                break
            tmp = os.path.dirname(tmp)

        is_ignored_flag = False

        for path_context in chain:
            rules = self._load_rules(path_context)
            if not rules:
                continue

            rel_to_context = os.path.relpath(file_or_dir_path, path_context).replace(os.sep, '/')
            name = os.path.basename(file_or_dir_path)

            for rule in rules:
                negate = rule.startswith('!')
                clean_rule = rule[1:] if negate else rule

                rule_is_dir = clean_rule.endswith('/')
                if rule_is_dir:
                    clean_rule = clean_rule[:-1]

                if not is_dir and rule_is_dir:
                    continue

                matched = False
                if '/' in clean_rule.strip('/'):
                    match_pattern = clean_rule.lstrip('/')
                    if fnmatch.fnmatch(rel_to_context, match_pattern) or fnmatch.fnmatch(rel_to_context, match_pattern + '/*'):
                        matched = True
                else:
                    rule_pattern = clean_rule.lstrip('/')
                    if fnmatch.fnmatch(name, rule_pattern) or fnmatch.fnmatch(rel_to_context, rule_pattern + '/*'):
                        matched = True

                if matched:
                    is_ignored_flag = not negate

        return is_ignored_flag


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert") or (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def convert_to_pdf(txt_path, pdf_path, display_name):
    if not PDF_SUPPORT:
        raise ImportError("fpdf2 and pypdf are required for generation")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=8)
    pdf.multi_cell(0, 5, f"File: {display_name}\n\n")

    wrapper = textwrap.TextWrapper(width=100, replace_whitespace=False, drop_whitespace=False)

    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            safe_line = line.rstrip('\n').replace('\t', '    ').encode("latin1", "replace").decode("latin1")
            if not safe_line:
                pdf.ln(5)
                continue

            wrapped_lines = wrapper.wrap(safe_line)
            for w_line in wrapped_lines:
                pdf.multi_cell(0, 5, w_line)

    pdf.output(pdf_path)


class MergeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text Merger GUI")
        self.root.geometry("650x650")

        self.config_path = "config.json"
        self.history_path = "history.json"
        self.config = load_config(self.config_path)
        self.history = self.load_history()
        self.cancel_flag = False
        self.last_output_path = None

        self.setup_ui()

    def reload_config(self):
        self.config = load_config(self.config_path)
        return self.config

    def load_history(self):
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_history(self, dir_path, out_name):
        self.history[dir_path] = out_name
        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f)
        except Exception as e:
            print(f"Failed to save history: {e}")

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        content = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        src_lbl = ctk.CTkLabel(content, text="Source Directory (Drag and Drop or Paste):")
        src_lbl.pack(anchor=tk.W, pady=(5, 2))
        self.dir_var = tk.StringVar()
        self.dir_var.trace_add("write", self.on_dir_change)

        dir_frame = ctk.CTkFrame(content, fg_color="transparent")
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        self.dir_combo = ctk.CTkComboBox(dir_frame, variable=self.dir_var, values=list(self.history.keys()))
        self.dir_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ctk.CTkButton(dir_frame, text="Open Folder", width=90, command=self.open_source_folder).pack(side=tk.RIGHT)
        ctk.CTkButton(dir_frame, text="Browse", width=80, command=self.browse_dir).pack(side=tk.RIGHT, padx=(0, 5))

        if TkinterDnD:
            self.dir_combo.drop_target_register(DND_FILES)
            self.dir_combo.dnd_bind('<<Drop>>', self.handle_drop)
            self.dir_combo.dnd_bind('<<DragEnter>>', self.on_drag_enter)
            self.dir_combo.dnd_bind('<<DragLeave>>', self.on_drag_leave)

        ext_lbl = ctk.CTkLabel(content, text="Target Extensions (e.g., .py, .txt):")
        ext_lbl.pack(anchor=tk.W, pady=(5, 2))
        Tooltip(ext_lbl, "Leave blank to merge all allowed files.")
        self.ext_var = tk.StringVar()
        self.ext_entry = ctk.CTkEntry(content, textvariable=self.ext_var)
        self.ext_entry.pack(fill=tk.X, pady=(0, 10))

        out_dir_lbl = ctk.CTkLabel(content, text="Output Directory:")
        out_dir_lbl.pack(anchor=tk.W, pady=(5, 2))
        self.out_dir_var = tk.StringVar(value=self.config.get("output_dir", "out"))

        out_dir_frame = ctk.CTkFrame(content, fg_color="transparent")
        out_dir_frame.pack(fill=tk.X, pady=(0, 10))
        self.out_dir_entry = ctk.CTkEntry(out_dir_frame, textvariable=self.out_dir_var)
        self.out_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        ctk.CTkButton(out_dir_frame, text="Open Folder", width=90, command=self.open_output_folder).pack(side=tk.RIGHT)
        ctk.CTkButton(out_dir_frame, text="Browse", width=80, command=self.browse_out_dir).pack(side=tk.RIGHT, padx=(0, 5))

        out_lbl = ctk.CTkLabel(content, text="Output File Name:")
        out_lbl.pack(anchor=tk.W, pady=(5, 2))
        self.out_var = tk.StringVar()
        self.out_combo = ctk.CTkComboBox(content, variable=self.out_var, values=[])
        self.out_combo.pack(fill=tk.X, pady=(0, 15))
        self.update_combo_list()

        self.recursive_var = tk.BooleanVar(value=True)
        rec_chk = ctk.CTkCheckBox(content, text="Recursive Search", variable=self.recursive_var)
        rec_chk.pack(anchor=tk.W, pady=(0, 5))
        Tooltip(rec_chk, "Include all folders inside the source directory")

        self.gitignore_var = tk.BooleanVar(value=self.config.get("use_gitignore", True))
        git_chk = ctk.CTkCheckBox(content, text="Use .gitignore rules", variable=self.gitignore_var)
        git_chk.pack(anchor=tk.W, pady=(0, 5))
        Tooltip(git_chk, "Automatically read and apply .gitignore files found in directories")

        self.pdf_var = tk.BooleanVar(value=False)
        self.pdf_var.trace_add("write", self.on_pdf_toggle)
        pdf_chk = ctk.CTkCheckBox(content, text="Merge into PDF (NotebookLM)", variable=self.pdf_var)
        pdf_chk.pack(anchor=tk.W, pady=(0, 15))
        if not PDF_SUPPORT:
            pdf_chk.configure(state=tk.DISABLED)
            Tooltip(pdf_chk, "Install fpdf2 and pypdf to enable this feature")
        else:
            Tooltip(pdf_chk, "Creates source PDFs and merges them into one final document")

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=(10, 10))

        ctk.CTkButton(btn_frame, text="Settings", width=80, command=self.open_settings).pack(side=tk.LEFT, padx=(0, 5))
        ctk.CTkButton(btn_frame, text="Preview", width=80, command=self.run_preview).pack(side=tk.LEFT, padx=5)

        ctk.CTkButton(btn_frame, text="Cancel", width=80, fg_color="#b71c1c",
                      hover_color="#7f0000", command=self.cancel_operation).pack(side=tk.RIGHT, padx=(5, 0))
        ctk.CTkButton(btn_frame, text="Merge Files", width=100, command=self.run_merge).pack(side=tk.RIGHT, padx=5)

        self.progress = ctk.CTkProgressBar(content, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(10, 15))
        self.progress.set(0)

        self.log_text = ctk.CTkTextbox(content, state=tk.DISABLED, height=150)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log_message(self, text):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def on_pdf_toggle(self, *args):
        current_name = self.out_var.get()
        if not current_name:
            return
        if self.pdf_var.get():
            if current_name.lower().endswith('.txt'):
                self.out_var.set(current_name[:-4] + '.pdf')
        else:
            if current_name.lower().endswith('.pdf'):
                self.out_var.set(current_name[:-4] + '.txt')

    def open_folder(self, path):
        if not path or not os.path.exists(path):
            self.log_message(f"Cannot open folder: Path does not exist ({path})")
            return

        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.call(["open", path])
            else:
                subprocess.call(["xdg-open", path])
        except Exception as e:
            self.log_message(f"Error opening folder: {e}")

    def open_source_folder(self):
        self.open_folder(self.dir_var.get())

    def open_output_folder(self):
        target_file = getattr(self, "last_output_path", None)
        path = self.out_dir_var.get()

        if target_file and os.path.exists(target_file):
            try:
                if sys.platform == "win32":
                    subprocess.call(["explorer", "/select,", os.path.normpath(target_file)])
                    return
                elif sys.platform == "darwin":
                    subprocess.call(["open", "-R", target_file])
                    return
                else:
                    subprocess.call(["xdg-open", os.path.dirname(target_file)])
                    return
            except Exception as e:
                self.log_message(f"Error revealing file: {e}")

        self.open_folder(path)

    def on_drag_enter(self, event):
        self.dir_combo.configure(fg_color="#3a7ebf")

    def on_drag_leave(self, event):
        self.dir_combo.configure(fg_color=ctk.ThemeManager.theme["CTkComboBox"]["fg_color"])

    def handle_drop(self, event):
        self.on_drag_leave(event)
        path = event.data.strip('{}')
        self.update_path_field(path)

    def browse_dir(self):
        current_path = self.dir_var.get()
        path = filedialog.askdirectory(initialdir=current_path if os.path.isdir(current_path) else None)
        if path:
            self.update_path_field(path)

    def browse_out_dir(self):
        current_path = self.out_dir_var.get()
        path = filedialog.askdirectory(initialdir=current_path if os.path.isdir(current_path) else None)
        if path:
            self.out_dir_var.set(os.path.normpath(path))

    def update_path_field(self, path):
        normalized = os.path.normpath(path)
        self.dir_var.set(normalized)

    def on_dir_change(self, *args):
        path = self.dir_var.get()
        is_pdf = self.pdf_var.get() if hasattr(self, 'pdf_var') else False

        if path in self.history:
            saved_name = self.history[path]
            if is_pdf and saved_name.endswith('.txt'):
                saved_name = saved_name[:-4] + '.pdf'
            elif not is_pdf and saved_name.endswith('.pdf'):
                saved_name = saved_name[:-4] + '.txt'
            self.out_var.set(saved_name)
        else:
            ext = ".pdf" if is_pdf else ".txt"
            if path:
                base = os.path.basename(os.path.normpath(path))
                if base:
                    self.out_var.set(f"{base}{ext}")
                    return

            default_out = self.config.get("output_file", "Mono.txt")
            if is_pdf and default_out.endswith('.txt'):
                default_out = default_out[:-4] + '.pdf'
            self.out_var.set(default_out)

    def update_combo_list(self):
        unique_names = list(set(self.history.values()))
        self.out_combo.configure(values=unique_names)
        self.dir_combo.configure(values=list(self.history.keys()))

    def cancel_operation(self):
        self.cancel_flag = True
        self.log_message("Requesting cancellation...")

    def run_preview(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)
        threading.Thread(target=self.execute_merge, args=(True,), daemon=True).start()

    def run_merge(self):
        directory = self.dir_var.get()
        if not os.path.isdir(directory):
            self.log_message("Error: Invalid Source Directory")
            return

        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)
        threading.Thread(target=self.execute_merge, args=(False,), daemon=True).start()

    def execute_merge(self, dry_run=False):
        self.progress.set(0)
        self.cancel_flag = False
        mode_text = "Previewing" if dry_run else "Merging"
        self.log_message(f"Starting {mode_text}...")

        try:
            directory = self.dir_var.get()
            ext = self.ext_var.get().strip() or None
            recursive = self.recursive_var.get()
            use_gitignore = self.gitignore_var.get()
            pdf_mode = self.pdf_var.get() if hasattr(self, 'pdf_var') else False

            ignore_set, ignored_ext_set, ignored_files = _get_ignore_config(self.config, None, None)
            skip_css = self.config.get("skip_css_if_no_ext", True)
            git_filter = GitIgnoreFilter(directory) if use_gitignore else None

            work_list = []
            if recursive:
                for root, dirs, files in os.walk(directory):
                    if git_filter:
                        dirs[:] = [d for d in dirs if not git_filter.is_ignored(os.path.join(root, d), is_dir=True)]

                    dirs[:] = [d for d in dirs if d not in ignore_set]
                    for f in files:
                        f_path = os.path.join(root, f)
                        if git_filter and git_filter.is_ignored(f_path, is_dir=False):
                            continue

                        if _is_file_included(f, root, directory, ext, ignore_set,
                                             ignored_ext_set, ignored_files, skip_css):
                            work_list.append(f_path)
            else:
                for f in os.listdir(directory):
                    f_path = os.path.join(directory, f)
                    if os.path.isfile(f_path):
                        if git_filter and git_filter.is_ignored(f_path, is_dir=False):
                            continue

                        if _is_file_included(f, directory, directory, ext, ignore_set,
                                             ignored_ext_set, ignored_files, skip_css):
                            work_list.append(f_path)

            total_files = len(work_list)
            if total_files == 0:
                self.log_message("No files found to process.")
                return

            processed_count = [0]

            def progress_callback():
                processed_count[0] += 1
                self.progress.set(processed_count[0] / total_files)

            final_out_path = merge_files(
                directory=directory,
                config=self.config,
                extension=ext,
                recursive=recursive,
                output_file=self.out_var.get(),
                cancel_check=lambda: self.cancel_flag,
                dry_run=dry_run,
                log_callback=self.log_message,
                item_callback=progress_callback,
                use_gitignore=use_gitignore,
                pdf_mode=pdf_mode
            )

            if self.cancel_flag:
                self.log_message("Operation Cancelled.")
            else:
                if not dry_run:
                    if final_out_path:
                        self.last_output_path = final_out_path
                        self.save_history(directory, os.path.basename(final_out_path))
                    self.update_combo_list()
                self.log_message("Merge completed successfully." if not dry_run else "Preview finished.")

        except Exception as e:
            self.log_message(f"Error: {e}")

    def open_settings(self):
        settings_win = ctk.CTkToplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("500x650")
        settings_win.transient(self.root)

        def create_textbox(parent, label_text, config_key):
            ctk.CTkLabel(parent, text=label_text).pack(anchor=tk.W, padx=20, pady=(10, 2))
            textbox = ctk.CTkTextbox(parent, height=80)
            textbox.pack(fill=tk.X, padx=20, pady=2)
            textbox.insert("1.0", ", ".join(self.config.get(config_key, [])))
            return textbox

        dirs_text = create_textbox(settings_win, "Ignored Directories (comma-separated):", "ignored_dirs")
        exts_text = create_textbox(settings_win, "Ignored Extensions (comma-separated):", "ignored_extensions")
        files_text = create_textbox(settings_win, "Ignored Files (comma-separated):", "ignored_files")

        temp_var = tk.BooleanVar(value=False)
        temp_chk = ctk.CTkCheckBox(settings_win, text="Temporary changes (until restart)", variable=temp_var)
        temp_chk.pack(anchor=tk.W, padx=20, pady=(15, 5))

        btn_frame = ctk.CTkFrame(settings_win, fg_color="transparent")
        btn_frame.pack(fill=tk.X, padx=20, pady=20)

        def save_settings():
            new_dirs = [d.strip() for d in dirs_text.get("1.0", tk.END).split(",") if d.strip()]
            new_exts = [e.strip() for e in exts_text.get("1.0", tk.END).split(",") if e.strip()]
            new_files = [f.strip() for f in files_text.get("1.0", tk.END).split(",") if f.strip()]

            self.config["ignored_dirs"] = new_dirs
            self.config["ignored_extensions"] = new_exts
            self.config["ignored_files"] = new_files

            if not temp_var.get():
                try:
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        json.dump(self.config, f, indent=2)
                    self.log_message("Settings saved successfully.")
                except Exception as e:
                    self.log_message(f"Failed to save settings: {e}")
            else:
                self.log_message("Temporary settings applied for this session.")

            settings_win.destroy()

        def reload_from_file():
            self.reload_config()

            dirs_text.delete("1.0", tk.END)
            dirs_text.insert("1.0", ", ".join(self.config.get("ignored_dirs", [])))

            exts_text.delete("1.0", tk.END)
            exts_text.insert("1.0", ", ".join(self.config.get("ignored_extensions", [])))

            files_text.delete("1.0", tk.END)
            files_text.insert("1.0", ", ".join(self.config.get("ignored_files", [])))

            self.log_message("Settings reloaded from file.")

        ctk.CTkButton(btn_frame, text="Reload from File", width=120, command=reload_from_file).pack(side=tk.LEFT, padx=(0, 10))
        ctk.CTkButton(btn_frame, text="Save Settings", width=120, command=save_settings).pack(side=tk.RIGHT)


def _get_ignore_config(config, ignore_dirs, ignore_exts):
    ignore_set = set(config.get("ignored_dirs", []))
    if ignore_dirs:
        for entry in ignore_dirs:
            if entry:
                parts = [p.strip() for p in entry.split(',') if p.strip()]
                ignore_set.update(parts)

    ignored_ext_set = set(config.get("ignored_extensions", []))
    if ignore_exts:
        for entry in ignore_exts:
            if entry:
                parts = [p.strip() for p in entry.split(',') if p.strip()]
                for p in parts:
                    ignored_ext_set.add(p if p.startswith('.') else f'.{p}')

    ignored_files = set(config.get("ignored_files", []))
    return ignore_set, ignored_ext_set, ignored_files


def _is_file_included(filename, root, directory, extension, ignore_set, ignored_ext_set, ignored_files, skip_css):
    if filename in ignored_files:
        return False

    lower = filename.lower()
    if any(lower.endswith(ext) for ext in ignored_ext_set):
        return False

    if extension is None and skip_css and lower.endswith('.css'):
        return False

    if extension is not None and not lower.endswith(extension):
        return False

    if root != directory:
        rel_root = os.path.relpath(root, directory)
        norm_parts = rel_root.split(os.sep)
        if any(part in ignore_set for part in norm_parts):
            return False

    return True


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
    pdf_mode=False
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
        pdf_temp_dir = os.path.join(out_dir, "pdf_sources")
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
                merger = PdfWriter()
                for p in pdf_list:
                    merger.append(p)
                merger.write(out_path)
                merger.close()
                shutil.rmtree(pdf_temp_dir)
                if log_callback:
                    log_callback("Source files cleaned up completely.")
            except Exception as e:
                if log_callback:
                    log_callback(f"Failed to join sources: {e}")

    finally:
        if outfile:
            outfile.close()

    return out_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Merge files via CLI or GUI.")
    parser.add_argument("directory", nargs="?", help="Directory to scan")
    parser.add_argument("extension", nargs="?", default=None)
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--gui", action="store_true", help="Force GUI mode")
    parser.add_argument("--no-gitignore", action="store_true", help="Disable auto reading of .gitignore files")
    parser.add_argument("--pdf", action="store_true", help="Merge into a single PDF")

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
        merge_files(args.directory, config=None, extension=args.extension, recursive=args.recursive, output_file=args.output, use_gitignore=not args.no_gitignore, pdf_mode=args.pdf)
