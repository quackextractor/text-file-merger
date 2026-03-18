#!/usr/bin/env python3
import os
import argparse
import json
import threading
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None

DEFAULT_CONFIG = {
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
    "skip_css_if_no_ext": True
}


def load_config(config_path="config.json"):
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception as e:
            print(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()


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
        self.root.geometry("650x650")

        self.config_path = "config.json"
        self.history_path = "history.json"
        self.config = load_config(self.config_path)
        self.history = self.load_history()
        self.cancel_flag = False

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
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Row 1: Source Directory
        src_lbl = ctk.CTkLabel(self.main_frame, text="Source Directory (Drag and Drop or Paste):")
        src_lbl.pack(anchor=tk.W, pady=(5, 2))
        self.dir_var = tk.StringVar()

        self.dir_var.trace_add("write", self.on_dir_change)

        dir_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        self.dir_combo = ctk.CTkComboBox(dir_frame, variable=self.dir_var, values=list(self.history.keys()))
        self.dir_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ctk.CTkButton(dir_frame, text="Browse", width=80, command=self.browse_dir).pack(side=tk.RIGHT)

        if TkinterDnD:
            self.dir_combo.drop_target_register(DND_FILES)
            self.dir_combo.dnd_bind('<<Drop>>', self.handle_drop)
            self.dir_combo.dnd_bind('<<DragEnter>>', self.on_drag_enter)
            self.dir_combo.dnd_bind('<<DragLeave>>', self.on_drag_leave)

        # Row 2: Target Extensions
        ext_lbl = ctk.CTkLabel(self.main_frame, text="Target Extensions (e.g., .py, .txt):")
        ext_lbl.pack(anchor=tk.W, pady=(5, 2))
        Tooltip(ext_lbl, "Leave blank to merge all allowed files.")
        self.ext_var = tk.StringVar()
        self.ext_entry = ctk.CTkEntry(self.main_frame, textvariable=self.ext_var)
        self.ext_entry.pack(fill=tk.X, pady=(0, 10))

        # Row 3: Output Directory
        out_dir_lbl = ctk.CTkLabel(self.main_frame, text="Output Directory:")
        out_dir_lbl.pack(anchor=tk.W, pady=(5, 2))

        self.out_dir_var = tk.StringVar(value=self.config.get("output_dir", "out"))

        out_dir_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        out_dir_frame.pack(fill=tk.X, pady=(0, 10))
        self.out_dir_entry = ctk.CTkEntry(out_dir_frame, textvariable=self.out_dir_var)
        self.out_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        ctk.CTkButton(out_dir_frame, text="Browse", width=80, command=self.browse_out_dir).pack(side=tk.RIGHT)

        # Row 4: Output File Name
        out_lbl = ctk.CTkLabel(self.main_frame, text="Output File Name:")
        out_lbl.pack(anchor=tk.W, pady=(5, 2))
        self.out_var = tk.StringVar()
        self.out_combo = ctk.CTkComboBox(self.main_frame, variable=self.out_var, values=[])
        self.out_combo.pack(fill=tk.X, pady=(0, 15))
        self.update_combo_list()

        # Options
        self.recursive_var = tk.BooleanVar(value=True)
        rec_chk = ctk.CTkCheckBox(self.main_frame, text="Recursive Search", variable=self.recursive_var)
        rec_chk.pack(anchor=tk.W, pady=(0, 15))
        Tooltip(rec_chk, "Include all folders inside the source directory")

        # Buttons
        btn_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=(10, 10))

        ctk.CTkButton(btn_frame, text="Settings", width=80, command=self.open_settings).pack(side=tk.LEFT, padx=(0, 5))
        ctk.CTkButton(btn_frame, text="Preview", width=80, command=self.run_preview).pack(side=tk.LEFT, padx=5)

        # Muted button color for integration with the dark theme
        ctk.CTkButton(btn_frame, text="Cancel", width=80, fg_color="#b71c1c",
                      hover_color="#7f0000", command=self.cancel_operation).pack(side=tk.RIGHT, padx=(5, 0))
        ctk.CTkButton(btn_frame, text="Merge Files", width=100, command=self.run_merge).pack(side=tk.RIGHT, padx=5)

        # Progress Indicator
        self.progress = ctk.CTkProgressBar(self.main_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(10, 15))
        self.progress.set(0)

        # Inline Status Log
        self.log_text = ctk.CTkTextbox(self.main_frame, state=tk.DISABLED, height=150)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log_message(self, text):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def on_drag_enter(self, event):
        self.dir_combo.configure(fg_color="#3a7ebf")

    def on_drag_leave(self, event):
        self.dir_combo.configure(fg_color=ctk.ThemeManager.theme["CTkComboBox"]["fg_color"])

    def handle_drop(self, event):
        self.on_drag_leave(event)
        path = event.data.strip('{}')
        self.update_path_field(path)

    def browse_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.update_path_field(path)

    def browse_out_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.out_dir_var.set(os.path.normpath(path))

    def update_path_field(self, path):
        normalized = os.path.normpath(path)
        self.dir_var.set(normalized)

    def on_dir_change(self, *args):
        path = self.dir_var.get()
        if path in self.history:
            self.out_var.set(self.history[path])
        else:
            self.out_var.set(self.config.get("output_file", "Mono.txt"))

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
        self.progress.start()
        self.cancel_flag = False
        mode_text = "Previewing" if dry_run else "Merging"
        self.log_message(f"Starting {mode_text}...")

        try:
            self.reload_config()
            self.config["output_dir"] = self.out_dir_var.get()
            ext = self.ext_var.get().strip() or None

            merge_files(
                directory=self.dir_var.get(),
                extension=ext,
                recursive=self.recursive_var.get(),
                output_file=self.out_var.get(),
                cancel_check=lambda: self.cancel_flag,
                dry_run=dry_run,
                log_callback=self.log_message
            )

            if self.cancel_flag:
                self.log_message("Operation Cancelled.")
            else:
                if not dry_run:
                    self.save_history(self.dir_var.get(), self.out_var.get())
                    self.update_combo_list()
                self.log_message("Merge completed successfully." if not dry_run else "Preview finished.")

        except Exception as e:
            self.log_message(f"Error: {e}")
        finally:
            self.progress.stop()

    def open_settings(self):
        settings_win = ctk.CTkToplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("450x450")
        settings_win.transient(self.root)

        ctk.CTkLabel(settings_win, text="Ignored Directories (comma-separated):").pack(
            anchor=tk.W, padx=20, pady=(20, 5)
        )
        dirs_text = ctk.CTkTextbox(settings_win, height=100)
        dirs_text.pack(fill=tk.X, padx=20, pady=5)
        dirs_text.insert("1.0", ", ".join(self.config.get("ignored_dirs", [])))

        ctk.CTkLabel(settings_win, text="Ignored Extensions (comma-separated):").pack(
            anchor=tk.W, padx=20, pady=(15, 5)
        )
        exts_text = ctk.CTkTextbox(settings_win, height=100)
        exts_text.pack(fill=tk.X, padx=20, pady=5)
        exts_text.insert("1.0", ", ".join(self.config.get("ignored_extensions", [])))

        def save_settings():
            new_dirs = [d.strip() for d in dirs_text.get("1.0", tk.END).split(",") if d.strip()]
            new_exts = [e.strip() for e in exts_text.get("1.0", tk.END).split(",") if e.strip()]
            self.config["ignored_dirs"] = new_dirs
            self.config["ignored_extensions"] = new_exts

            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2)
                self.reload_config()
                self.log_message("Settings saved successfully.")
            except Exception as e:
                self.log_message(f"Failed to save settings: {e}")
            settings_win.destroy()

        ctk.CTkButton(settings_win, text="Save Settings", command=save_settings).pack(pady=20)


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

    # Check parent directories for recursive ignore
    if root != directory:
        rel_root = os.path.relpath(root, directory)
        norm_parts = rel_root.split(os.sep)
        if any(part in ignore_set for part in norm_parts):
            return False

    return True


def _merge_recursive(directory, extension, ignore_set, ignored_ext_set, ignored_files, skip_css,
                     cancel_check, dry_run, log_callback, outfile):
    for root, dirs, files in os.walk(directory):
        if cancel_check and cancel_check():
            break

        dirs[:] = [d for d in dirs if d not in ignore_set]
        for file in files:
            if cancel_check and cancel_check():
                break

            if _is_file_included(file, root, directory, extension, ignore_set,
                                 ignored_ext_set, ignored_files, skip_css):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, directory)
                _merge_single_file(outfile, file_path, rel_path, dry_run, log_callback)


def _merge_flat(directory, extension, ignore_set, ignored_ext_set, ignored_files, skip_css,
                cancel_check, dry_run, log_callback, outfile):
    for entry in os.listdir(directory):
        if cancel_check and cancel_check():
            break

        if entry in ignore_set:
            continue

        full_path = os.path.join(directory, entry)
        if not os.path.isfile(full_path):
            continue

        if _is_file_included(entry, directory, directory, extension, ignore_set,
                             ignored_ext_set, ignored_files, skip_css):
            _merge_single_file(outfile, full_path, entry, dry_run, log_callback)


def merge_files(
    directory,
    extension=None,
    recursive=False,
    output_file=None,
    ignore_dirs=None,
    ignore_exts=None,
    cancel_check=None,
    dry_run=False,
    log_callback=None
):
    config = load_config()
    raw_out_path = output_file or config.get("output_file", "Mono.txt")
    out_dir = config.get("output_dir", "out")
    out_path = os.path.join(out_dir, os.path.basename(raw_out_path))

    ignore_set, ignored_ext_set, ignored_files = _get_ignore_config(config, ignore_dirs, ignore_exts)
    skip_css = config.get("skip_css_if_no_ext", True)

    if extension and not extension.startswith('.'):
        extension = f'.{extension}'

    outfile = None
    try:
        if not dry_run:
            os.makedirs(out_dir, exist_ok=True)
            outfile = open(out_path, "w", encoding="utf-8")

        if recursive:
            _merge_recursive(directory, extension, ignore_set, ignored_ext_set, ignored_files,
                             skip_css, cancel_check, dry_run, log_callback, outfile)
        else:
            _merge_flat(directory, extension, ignore_set, ignored_ext_set, ignored_files,
                        skip_css, cancel_check, dry_run, log_callback, outfile)
    finally:
        if outfile:
            outfile.close()


def _merge_single_file(outfile, file_path, display_name, dry_run, log_callback):
    if dry_run:
        if log_callback:
            log_callback(f"Would merge: {display_name}")
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Merge files via CLI or GUI.")
    parser.add_argument("directory", nargs="?", help="Directory to scan")
    parser.add_argument("extension", nargs="?", default=None)
    parser.add_argument("-r", "--recursive", action="store_true")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--gui", action="store_true", help="Force GUI mode")

    args, unknown = parser.parse_known_args()

    if args.gui or not args.directory:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        if TkinterDnD:
            root = TkinterDnD.Tk()
            # A background fix so standard Tk matches CTk
            root.configure(bg=ctk.ThemeManager.theme["CTk"]["fg_color"][0])
        else:
            root = ctk.CTk()

        app = MergeApp(root)
        root.mainloop()
    else:
        merge_files(args.directory, args.extension, args.recursive, args.output)
