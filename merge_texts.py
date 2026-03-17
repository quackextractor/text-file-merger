#!/usr/bin/env python3
import os
import argparse
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    TkinterDnD = None

class MergeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text Merger GUI")
        self.root.geometry("600x450")
        
        self.config_path = "config.json"
        self.history_path = "history.json"
        self.config = self.load_config()
        self.history = self.load_history()

        self.setup_ui()

    def load_config(self):
        default_config = {
            "output_file": "Mono.txt",
            "ignored_dirs": [],
            "ignored_files": [],
            "ignored_extensions": [],
            "skip_css_if_no_ext": True
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return {**default_config, **json.load(f)}
            except Exception as e:
                print(f"Error loading config: {e}")
        return default_config

    def load_history(self):
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
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
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Source Directory (Drag & Drop or Paste):").pack(anchor=tk.W)
        self.dir_var = tk.StringVar()
        self.dir_var.trace_add("write", self.on_dir_change)
        self.dir_entry = ttk.Entry(main_frame, textvariable=self.dir_var)
        self.dir_entry.pack(fill=tk.X, pady=(5, 15))

        if TkinterDnD:
            self.dir_entry.drop_target_register(DND_FILES)
            self.dir_entry.dnd_bind('<<Drop>>', self.handle_drop)

        ttk.Label(main_frame, text="Output File Name:").pack(anchor=tk.W)
        self.out_var = tk.StringVar()
        self.out_combo = ttk.Combobox(main_frame, textvariable=self.out_var)
        self.out_combo.pack(fill=tk.X, pady=(5, 15))
        self.update_combo_list()

        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="Recursive Search", variable=self.recursive_var).pack(anchor=tk.W)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=20)
        
        ttk.Button(btn_frame, text="Browse", command=self.browse_dir).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Merge Files", command=self.run_merge).pack(side=tk.RIGHT, padx=5)

    def handle_drop(self, event):
        path = event.data.strip('{}')
        self.update_path_field(path)

    def browse_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.update_path_field(path)

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
        self.out_combo['values'] = unique_names

    def run_merge(self):
        directory = self.dir_var.get()
        output = self.out_var.get()

        if not os.path.isdir(directory):
            messagebox.showerror("Error", "Invalid Source Directory")
            return

        try:
            merge_files(
                directory=directory,
                recursive=self.recursive_var.get(),
                output_file=output
            )
            self.save_history(directory, output)
            self.update_combo_list()
            
            final_file_name = os.path.basename(output) if output else self.config.get("output_file", "Mono.txt")
            messagebox.showinfo("Success", f"Files merged into out/{final_file_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Merge failed: {e}")

def load_config(config_path="config.json"):
    default_config = {
        "output_file": "Mono.txt",
        "ignored_dirs": [],
        "ignored_files": [],
        "ignored_extensions": [],
        "skip_css_if_no_ext": True
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return {**default_config, **json.load(f)}
        except Exception as e:
            print(f"Error loading config: {e}")
    return default_config

def merge_files(
    directory,
    extension=None,
    recursive=False,
    output_file=None,
    ignore_dirs=None,
    ignore_exts=None
):
    config = load_config()
    raw_out_path = output_file or config.get("output_file", "Mono.txt")
    
    out_dir = "out"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, os.path.basename(raw_out_path))

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
    skip_css = config.get("skip_css_if_no_ext", True)

    if extension and not extension.startswith('.'):
        extension = f'.{extension}'

    with open(out_path, "w", encoding="utf-8") as outfile:
        if recursive:
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if d not in ignore_set]
                norm_parts = os.path.normpath(root).split(os.sep)
                if any(part in ignore_set for part in norm_parts):
                    continue

                for file in files:
                    if file in ignored_files:
                        continue
                    lower = file.lower()
                    if any(lower.endswith(ext) for ext in ignored_ext_set):
                        continue
                    if extension is None and skip_css and lower.endswith('.css'):
                        continue
                    if extension is None or lower.endswith(extension):
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, directory)
                        outfile.write(f"----- {rel_path} -----\n")
                        try:
                            with open(file_path, "r", encoding="utf-8") as infile:
                                outfile.write(infile.read())
                        except Exception as e:
                            outfile.write(f"[Error reading file: {e}]\n")
                        outfile.write("\n")
        else:
            for entry in os.listdir(directory):
                if entry in ignored_files or entry in ignore_set:
                    continue
                lower = entry.lower()
                if any(lower.endswith(ext) for ext in ignored_ext_set):
                    continue
                file_path = os.path.join(directory, entry)
                if extension is None and skip_css and lower.endswith('.css'):
                    continue
                if os.path.isfile(file_path) and (extension is None or lower.endswith(extension)):
                    outfile.write(f"----- {entry} -----\n")
                    try:
                        with open(file_path, "r", encoding="utf-8") as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"[Error reading file: {e}]\n")
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
        if TkinterDnD:
            root = TkinterDnD.Tk()
        else:
            root = tk.Tk()
        app = MergeApp(root)
        root.mainloop()
    else:
        merge_files(args.directory, args.extension, args.recursive, args.output)