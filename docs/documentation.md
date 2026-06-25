# Text File Merger - Performance & Architecture Documentation

This document outlines the architecture, pipeline stages, and performance optimizations implemented in version 1.5.0 of the Text File Merger utility.

## 1. Architectural Overview

The application is structured into a clean modular package under the `src/` directory, with `main.py` serving as the primary entry point:

- **Entry Point (`main.py`)**: Handles command line argument parsing and starts the Tkinter GUI (`MergeApp`) or executes the CLI-based merge directly.
- **Collector (`src/collector.py`)**: Runs Phase 1 (pre-scan) of the merging process, walking the file tree, applying ignore rules, and building a deterministic ordered list of file tasks.
- **Config (`src/config.py`)**: Manages default configuration settings and handles configuration loading and deep merging of performance configurations.
- **Filters (`src/filters.py`)**: Contains ignore filters, including cache-backed pattern compilation for `.gitignore` rules.
- **Merger (`src/merger.py`)**: Orchestrates the merge pipeline, coordinating sequential streaming, parallel worker execution, atomic filesystem updates, and cancellation events.
- **PDF Utilities (`src/pdf_utils.py`)**: Contains fpdf2 and pypdf helpers, including parallel fpdf2 worker routines and memory-bounded batch PDF joining.
- **GUI (`src/gui.py`)**: CustomTkinter-based interface incorporating event-driven cancellation and non-blocking background threading utilizing a UI update throttler.

---

## 2. Merging Pipeline & Performance Optimizations

### 2.1 Phase 1: Pre-Scan (Collector)
To support deterministic file order, accurate progress reports, and safe parallelization, the application implements a two-phase pipeline:
1. The `collect_files` function traverses the directories recursively or flatly.
2. Directories and files are sorted alphabetically at each level to guarantee consistent, cross-platform ordering.
3. Path exclusion filters (like `.gitignore` rules and config ignores) are matched against cached pre-compiled regex translations of glob patterns, achieving constant-time lookup.
4. Filtered files are compiled into a deterministic list of `FileTask` objects, each carrying its file size and classification (`text`, `docx`, `doc`, or `other_text`).

### 2.2 Phase 2: Parallel Text Merging & Streaming
When merging plain text:
- **ThreadPoolExecutor**: Files smaller than the `large_file_threshold` are queued into a thread pool (I/O-bound workers).
- **Priority Queue & Sorted Writing**: Workers push extracted text into a thread-safe `PriorityQueue` keyed by task index. The main writer thread polls this queue and writes contents in deterministic order.
- **Large-File Streaming**: Files exceeding the threshold bypass the thread pool and memory buffers. They are streamed directly into the destination file using `shutil.copyfileobj` with a optimized buffer size, ensuring the application remains memory-safe.
- **Atomic Operations**: Merges write to `<output>.tmp`. Upon successful, error-free completion, `os.replace` replaces the destination file atomically. If cancelled or aborted, the temporary file is immediately removed.

### 2.3 Phase 3: PDF Generation Acceleration
For PDF compilations:
- **Batch LibreOffice Conversion**: Multiple Word (`.doc`/`.docx`) files are converted in a single headless `soffice` subprocess invocation using a temporary directory staging layout to avoid basename collisions.
- **Parallel Plain-PDF Conversions**: Plain text files are compiled into individual PDFs in parallel using a `ThreadPoolExecutor` (or `ProcessPoolExecutor` for larger datasets).
- **Chunk-Based PDF Joining**: If the count of compiled PDFs exceeds the `pdf_batch_threshold`, files are joined in chunks of 50 into intermediate batch PDFs, reducing peak RAM consumption before joining them into the final file.

### 2.4 Phase 4: GUI Responsiveness
- **ProgressThrottler**: GUI updates and logging messages are accumulated and pushed to the main thread via `Tk.after` every 100ms. This prevents the UI message loop from being overwhelmed during fast, sequential operations.
- **Responsive Cancellation**: A `threading.Event` is passed down to all execution blocks. Workers periodically check `cancel_event.is_set()` and exit promptly. Active subprocesses are terminated immediately using process handles.

---

## 3. Configuration Parameters

The `performance` dictionary in `config.json` exposes the following variables:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_workers` | int | `0` | Thread/process count (0 sets auto-detection based on CPU count) |
| `large_file_threshold_mb` | int | `5` | Size above which text files are streamed sequentially |
| `output_buffer_kb` | int | `256` | Buffer size used when writing the output file |
| `progress_update_interval_ms` | int | `100` | Minimum duration in milliseconds between GUI refreshes |
| `batch_libreoffice` | bool | `true` | Enable batch conversion of Word documents in LibreOffice |
| `parallel_pdf_fallback` | bool | `true` | Run plain PDF fallback compilation in parallel |
| `min_tasks_for_parallel` | int | `8` | Minimum file count required to trigger parallel text merging |
| `pdf_batch_threshold` | int | `200` | File count above which PDF joining is split into batches of 50 |
