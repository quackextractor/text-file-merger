# Text File Merger

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/quackextractor/text-file-merger)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A powerful and user-friendly utility to merge multiple text-based files into a single document. Whether you are a developer consolidating source code or a writer organizing notes, this tool simplifies the process with both Command Line (CLI) and Graphical User (GUI) interfaces.

## Features

- **Modern Themed GUI**: Beautiful Interface powered by `CustomTkinter` for a sleek experience.
- **Background Operations**: Non-blocking threading keeps the app responsive during heavy merges.
- **Drag & Drop Support**: Drop folders to select your source directory with visual feedback.
- **File Preview**: Dry-run mode allows you to see exactly which files will be merged.
- **In-App Settings**: Configure ignored folders and extensions directly within the project.
- **Output Management**: Explicitly choose your output directory and filename in the GUI.
- **Progress Tracking**: Real-time progress bar and inline logs for continuous status updates.
- **Recursive Merging**: Scan through nested directories to capture all relevant content.
- **Smart Filtering**: Custom ignore lists for files, folders, and specific extensions.
- **History Tracking**: Automatically remembers your previous configurations for quick access.
- **CLI Mode**: Full-featured command-line support for advanced users and automation.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/quackextractor/text-file-merger.git
   cd text-file-merger
   ```

2. **(Optionally) Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: For drag-and-drop support, `tkinterdnd2` is required.*

## Usage

### GUI Mode (Default)
Run without arguments to launch the graphical interface:
```bash
python merge_texts.py
```

### CLI Mode
Merge all files in a directory recursively:
```bash
python merge_texts.py path/to/source -r -o MyMergedFile.txt
```

#### CLI Arguments:
- `directory`: The source directory to scan.
- `extension` (Optional): Filter by a specific file extension (e.g., `.py`).
- `-r`, `--recursive`: Search subdirectories recursively.
- `-o`, `--output`: Specify the output filename (saved in the `out/` folder).

## Configuration

Modify `config.json` to customize the behavior:
- `output_dir`: Directory where merged files are saved (default: `out`).
- `ignored_dirs`: List of directories to skip.
- `ignored_files`: List of specific files to ignore.
- `ignored_extensions`: List of file extensions to always skip.

## Development

### Prerequisites
- Python 3.8 or higher
- `tkinter` (usually bundled with Python)
- `tkinterdnd2-universal` (for GUI drag-and-drop)

### Testing
Run the test suite using `pytest`:
```bash
pytest tests/
```

### Linting
Check code quality using `flake8`:
```bash
flake8 merge_texts.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Miro Slezák**
