# Text File Merger

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/quackextractor/text-file-merger)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A powerful and user-friendly utility to merge multiple text-based files into a single document. Whether you are a developer consolidating source code or a writer organizing notes, this tool simplifies the process with both Command Line (CLI) and Graphical User (GUI) interfaces.

## Features

- **Dual-Mode Interface**: Use it as a CLI tool for automation or a GUI for drag-and-drop simplicity.
- **Drag & Drop Support**: Easily drop folders into the GUI to select the source directory.
- **Recursive Merging**: Scan through nested directories to capture all relevant content.
- **Smart Filtering**: Automatic exclusion of binary files, large directories (like `node_modules`), and specific extensions.
- **Configurable**: Fully customize ignored files, directories, and output settings via `config.json`.
- **History Tracking**: Remembers previously used output names for different directories.

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
