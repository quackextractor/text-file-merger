import sys
import os
import json
import threading
import subprocess
import time
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None

from src.config import load_config
from src.filters import GitIgnoreFilter, _get_ignore_config, _is_file_included
from src.merger import merge_files
from src.pdf_utils import PDF_SUPPORT


class ProgressThrottler:
    def __init__(self, progress_widget, log_widget, root, min_interval_ms=100):
        self.progress = progress_widget
        self.log = log_widget
        self.root = root
        self.min_interval = min_interval_ms / 1000
        self._last_flush = 0
        self._lock = threading.Lock()
        self._pending_progress = 0.0
        self._logs = []

    def report(self, progress_value, message=None):
        with self._lock:
            self._pending_progress = progress_value
            if message:
                self._logs.append(message)
            now = time.time()
            if now - self._last_flush < self.min_interval:
                return
            self._last_flush = now
        self.root.after(0, self._flush)

    def force_flush(self):
        self.root.after(0, self._flush)

    def _flush(self):
        with self._lock:
            val = self._pending_progress
            msgs = self._logs[:]
            self._logs.clear()
        self.progress.set(val)
        if msgs:
            self.log.configure(state=tk.NORMAL)
            for msg in msgs:
                self.log.insert(tk.END, msg + "\n")
            self.log.see(tk.END)
            self.log.configure(state=tk.DISABLED)


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


class MergeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text Merger GUI")
        self.root.geometry("650x800")

        self.config_path = "config.json"
        self.history_path = "history.json"
        self.config = load_config(self.config_path)
        self.history = self.load_history()
        self.cancel_event = threading.Event()
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

        self.src_lbl = ctk.CTkLabel(content, text="Source Directory (Drag and Drop or Paste):")
        self.src_lbl.pack(anchor=tk.W, pady=(5, 2))
        self.dir_var = tk.StringVar()
        self.dir_var.trace_add("write", self.on_dir_change)

        dir_frame = ctk.CTkFrame(content, fg_color="transparent")
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        self.dir_combo = ctk.CTkComboBox(dir_frame, variable=self.dir_var, values=list(self.history.keys()))
        self.dir_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.open_src_btn = ctk.CTkButton(dir_frame, text="Open Folder", width=90, command=self.open_source_folder)
        self.open_src_btn.pack(side=tk.RIGHT)
        self.browse_src_btn = ctk.CTkButton(dir_frame, text="Browse", width=80, command=self.browse_dir)
        self.browse_src_btn.pack(side=tk.RIGHT, padx=(0, 5))

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

        self.skip_css_var = tk.BooleanVar(value=self.config.get("skip_css_if_no_ext", True))
        skip_css_chk = ctk.CTkCheckBox(content, text="Skip CSS files when no target ext.", variable=self.skip_css_var)
        skip_css_chk.pack(anchor=tk.W, pady=(0, 5))
        Tooltip(skip_css_chk, "If checked, .css files are ignored unless a specific extension filter is set.")

        self.is_git_var = tk.BooleanVar(value=False)
        self.is_git_var.trace_add("write", self.on_git_toggle)
        self.git_repo_chk = ctk.CTkCheckBox(content, text="Git Repository", variable=self.is_git_var)
        self.git_repo_chk.pack(anchor=tk.W, pady=(0, 5))
        Tooltip(self.git_repo_chk, "Clone and merge from a remote Git repository URL")

        # Git Ref and Token Inputs sub-frame (hidden by default)
        self.git_frame = ctk.CTkFrame(content, fg_color="transparent")

        git_ref_lbl = ctk.CTkLabel(self.git_frame, text="Ref (Branch/Tag/Commit):")
        git_ref_lbl.pack(side=tk.LEFT, padx=(0, 5))
        self.git_ref_var = tk.StringVar()
        self.git_ref_entry = ctk.CTkEntry(self.git_frame, textvariable=self.git_ref_var, width=120)
        self.git_ref_entry.pack(side=tk.LEFT, padx=(0, 10))

        git_token_lbl = ctk.CTkLabel(self.git_frame, text="Token:")
        git_token_lbl.pack(side=tk.LEFT, padx=(0, 5))
        self.git_token_var = tk.StringVar()
        self.git_token_entry = ctk.CTkEntry(self.git_frame, textvariable=self.git_token_var, show="*", width=120)
        self.git_token_entry.pack(side=tk.LEFT)

        self.include_tree_var = tk.BooleanVar(value=self.config.get("include_tree", True))
        tree_chk = ctk.CTkCheckBox(content, text="Include directory tree", variable=self.include_tree_var)
        tree_chk.pack(anchor=tk.W, pady=(0, 5))
        Tooltip(tree_chk, "Prepend a visual folder hierarchy tree to the output")

        self.keep_txt_sources_var = tk.BooleanVar(value=False)
        self.keep_txt_chk = ctk.CTkCheckBox(content, text="Keep source text files", variable=self.keep_txt_sources_var)
        self.keep_txt_chk.pack(anchor=tk.W, pady=(0, 5))

        self.pdf_var = tk.BooleanVar(value=False)
        self.pdf_var.trace_add("write", self.on_pdf_toggle)
        pdf_chk = ctk.CTkCheckBox(content, text="Merge into PDF (NotebookLM)", variable=self.pdf_var)
        pdf_chk.pack(anchor=tk.W, pady=(0, 5))

        self.keep_sources_var = tk.BooleanVar(value=False)
        self.keep_chk = ctk.CTkCheckBox(content, text="Keep source PDFs", variable=self.keep_sources_var, state=tk.DISABLED)
        self.keep_chk.pack(anchor=tk.W, padx=20, pady=(0, 5))

        self.styled_pdf_var = tk.BooleanVar(value=False)
        self.styled_chk = ctk.CTkCheckBox(content, text="Styled PDF Formatting (MS Word or LibreOffice needed)", variable=self.styled_pdf_var, state=tk.DISABLED)
        self.styled_chk.pack(anchor=tk.W, padx=20, pady=(0, 15))

        if not PDF_SUPPORT:
            pdf_chk.configure(state=tk.DISABLED)
            Tooltip(pdf_chk, "Install fpdf2 and pypdf to enable this feature")
        else:
            Tooltip(pdf_chk, "Creates source PDFs and merges them into one final document")
            Tooltip(self.keep_chk, "Preserves the individual compiled source PDF files in the output directory")
            Tooltip(self.styled_chk, "Applies modern fonts and styling to the output PDF instead of raw text")

        Tooltip(self.keep_txt_chk, "Preserves the individual parsed source text files in the output directory")

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

        # Log & Summary side-by-side frame
        log_summary_frame = ctk.CTkFrame(content, fg_color="transparent")
        log_summary_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Left: Log textbox
        self.log_text = ctk.CTkTextbox(log_summary_frame, state=tk.DISABLED, height=150)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Right: Summary frame
        self.summary_frame = ctk.CTkFrame(log_summary_frame, width=240)
        self.summary_frame.pack(side=tk.RIGHT, fill=tk.BOTH)
        self.summary_frame.pack_propagate(False)

        summary_title = ctk.CTkLabel(self.summary_frame, text="Merge / Preview Summary", font=("Helvetica", 12, "bold"))
        summary_title.pack(anchor=tk.W, padx=10, pady=(10, 5))

        self.summary_files_lbl = ctk.CTkLabel(self.summary_frame, text="Files Processed: -", font=("Helvetica", 11), anchor=tk.W)
        self.summary_files_lbl.pack(fill=tk.X, padx=10, pady=2)

        self.summary_size_lbl = ctk.CTkLabel(self.summary_frame, text="Total Size: -", font=("Helvetica", 11), anchor=tk.W)
        self.summary_size_lbl.pack(fill=tk.X, padx=10, pady=2)

        self.summary_tokens_lbl = ctk.CTkLabel(self.summary_frame, text="Estimated Tokens: -", font=("Helvetica", 11), anchor=tk.W)
        self.summary_tokens_lbl.pack(fill=tk.X, padx=10, pady=2)

        self.summary_path_lbl = ctk.CTkLabel(self.summary_frame, text="Output: -", font=("Helvetica", 11), anchor=tk.W, wraplength=220)
        self.summary_path_lbl.pack(fill=tk.X, padx=10, pady=2)

        self.tree_label = ctk.CTkLabel(content, text="Directory Structure:")
        self.tree_label.pack(anchor=tk.W, pady=(5, 2))
        self.tree_text = ctk.CTkTextbox(content, state=tk.DISABLED, height=120)
        self.tree_text.pack(fill=tk.BOTH, expand=True)

    def log_message(self, text):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def on_git_toggle(self, *args):
        if self.is_git_var.get():
            self.src_lbl.configure(text="Source Git URL (http/https):")
            self.git_frame.pack(fill=tk.X, pady=(0, 10))
            self.browse_src_btn.configure(state=tk.DISABLED)
            self.open_src_btn.configure(state=tk.DISABLED)
        else:
            self.src_lbl.configure(text="Source Directory (Drag and Drop or Paste):")
            self.git_frame.pack_forget()
            self.browse_src_btn.configure(state=tk.NORMAL)
            self.open_src_btn.configure(state=tk.NORMAL)

    def on_pdf_toggle(self, *args):
        current_name = self.out_var.get()
        if current_name:
            if self.pdf_var.get():
                if current_name.lower().endswith('.txt'):
                    self.out_var.set(current_name[:-4] + '.pdf')
            else:
                if current_name.lower().endswith('.pdf'):
                    self.out_var.set(current_name[:-4] + '.txt')

        if hasattr(self, 'keep_chk'):
            if self.pdf_var.get():
                self.keep_chk.configure(state=tk.NORMAL)
                if hasattr(self, 'styled_chk'):
                    self.styled_chk.configure(state=tk.NORMAL)
            else:
                self.keep_chk.configure(state=tk.DISABLED)
                self.keep_sources_var.set(False)
                if hasattr(self, 'styled_chk'):
                    self.styled_chk.configure(state=tk.DISABLED)
                    self.styled_pdf_var.set(False)

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
        self.cancel_event.set()
        self.log_message("Requesting cancellation...")

    def run_preview(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)
        threading.Thread(target=self.execute_merge, args=(True,), daemon=True).start()

    def run_merge(self):
        directory = self.dir_var.get()
        is_git = self.is_git_var.get() or (directory and (directory.startswith("http://") or directory.startswith("https://")))
        if not is_git and not os.path.isdir(directory):
            self.log_message("Error: Invalid Source Directory")
            return

        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)
        threading.Thread(target=self.execute_merge, args=(False,), daemon=True).start()

    def execute_merge(self, dry_run=False):
        self.progress.set(0)
        self.cancel_event.clear()
        self.tree_text.configure(state=tk.NORMAL)
        self.tree_text.delete("1.0", tk.END)
        self.tree_text.configure(state=tk.DISABLED)

        # Clear summary labels
        self.summary_files_lbl.configure(text="Files Processed: -")
        self.summary_size_lbl.configure(text="Total Size: -")
        self.summary_tokens_lbl.configure(text="Estimated Tokens: -")
        self.summary_path_lbl.configure(text="Output: -")

        mode_text = "Previewing" if dry_run else "Merging"
        self.log_message(f"Starting {mode_text}...")

        try:
            directory = self.dir_var.get()
            ext = self.ext_var.get().strip() or None
            recursive = self.recursive_var.get()
            use_gitignore = self.gitignore_var.get()
            pdf_mode = self.pdf_var.get() if hasattr(self, 'pdf_var') else False
            keep_sources = self.keep_sources_var.get() if hasattr(self, 'keep_sources_var') else False
            keep_txt_sources = self.keep_txt_sources_var.get() if hasattr(self, 'keep_txt_sources_var') else False
            styled_pdf = self.styled_pdf_var.get() if hasattr(self, 'styled_pdf_var') else False
            include_tree = self.include_tree_var.get() if hasattr(self, 'include_tree_var') else True

            is_git = self.is_git_var.get() or (directory and (directory.startswith("http://") or directory.startswith("https://")))
            git_branch = self.git_ref_var.get().strip() or None if is_git else None
            git_token = self.git_token_var.get().strip() or None if is_git else None

            tasks = None
            total_files = 0

            # If it's a local folder, pre-collect tasks to know progress.
            if not is_git:
                ignore_set, ignored_ext_tuple, ignored_files = _get_ignore_config(self.config, None, None)
                skip_css = self.skip_css_var.get()
                git_filter = GitIgnoreFilter(directory) if use_gitignore else None

                from src.collector import collect_files
                tasks = collect_files(
                    directory=directory,
                    extension=ext,
                    recursive=recursive,
                    ignore_set=ignore_set,
                    ignored_ext_tuple=ignored_ext_tuple,
                    ignored_files=ignored_files,
                    skip_css=skip_css,
                    git_filter=git_filter
                )
                total_files = len(tasks)
                if total_files == 0:
                    self.log_message("No files found to process.")
                    return

            perf = self.config.get("performance", {})
            interval_ms = perf.get("progress_update_interval_ms", 100)
            throttler = ProgressThrottler(self.progress, self.log_text, self.root, interval_ms)

            processed_count = 0

            def tasks_collected_callback(collected_tasks):
                nonlocal total_files
                total_files = len(collected_tasks)

            def item_callback():
                nonlocal processed_count
                processed_count += 1
                if total_files > 0:
                    progress_val = processed_count / total_files
                    throttler.report(progress_val)
                else:
                    throttler.report(0.0)

            def throttled_log(msg):
                if total_files > 0:
                    progress_val = processed_count / total_files
                    throttler.report(progress_val, msg)
                else:
                    throttler.report(0.0, msg)

            res = merge_files(
                directory=directory,
                config=self.config,
                extension=ext,
                recursive=recursive,
                output_file=self.out_var.get(),
                cancel_event=self.cancel_event,
                dry_run=dry_run,
                log_callback=throttled_log,
                item_callback=item_callback,
                use_gitignore=use_gitignore,
                pdf_mode=pdf_mode,
                keep_pdf_sources=keep_sources,
                keep_txt_sources=keep_txt_sources,
                styled_pdf=styled_pdf,
                tasks=tasks,
                is_git=is_git,
                git_branch=git_branch,
                git_token=git_token,
                include_tree=include_tree,
                tasks_collected_callback=tasks_collected_callback
            )

            throttler.force_flush()

            if self.cancel_event.is_set():
                self.log_message("Operation Cancelled.")
                self.progress.set(0)
            else:
                if res:
                    final_out_path = res["output_path"]
                    if not dry_run:
                        self.last_output_path = final_out_path
                        self.save_history(directory, os.path.basename(final_out_path))
                        self.update_combo_list()

                    # Update directory tree text box
                    if "tree" in res and res["tree"]:
                        self.tree_text.configure(state=tk.NORMAL)
                        self.tree_text.delete("1.0", tk.END)
                        self.tree_text.insert(tk.END, res["tree"])
                        self.tree_text.configure(state=tk.DISABLED)

                    # Format estimated tokens
                    token_val = res["token_count"]
                    if token_val >= 1000:
                        formatted_tokens = f"{token_val / 1000:.1f}k"
                    else:
                        formatted_tokens = str(token_val)

                    # Update summary labels
                    self.summary_files_lbl.configure(text=f"Files Processed: {res['file_count']}")
                    self.summary_size_lbl.configure(text=f"Total Size: {res['total_size_bytes'] / 1024:.1f} KB")
                    self.summary_tokens_lbl.configure(text=f"Estimated Tokens: {formatted_tokens}")
                    if not dry_run:
                        self.summary_path_lbl.configure(text=f"Output: {os.path.basename(final_out_path)}")
                    else:
                        self.summary_path_lbl.configure(text="Output: Preview")

                    # Update log with summary
                    mode_name = "Preview" if dry_run else "Merge"
                    self.log_message(f"\n--- {mode_name} Summary ---")
                    self.log_message(f"Files processed: {res['file_count']}")
                    self.log_message(f"Total size: {res['total_size_bytes'] / 1024:.1f} KB")
                    self.log_message(f"Estimated tokens: {formatted_tokens}")
                    if not dry_run:
                        self.log_message(f"Output path: {final_out_path}\n")
                    else:
                        self.log_message("Preview finished.\n")
                else:
                    self.log_message("Operation completed with no output.")

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
