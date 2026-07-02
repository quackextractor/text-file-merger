# Text File Merger

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.8.0-blue.svg)](https://github.com/quackextractor/text-file-merger)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A powerful and user-friendly utility to merge multiple text-based files into a single document. Whether you are a developer consolidating source code or a writer organizing notes, this tool simplifies the process with both Command Line (CLI) and Graphical User (GUI) interfaces.

## Features

- **Modern Themed GUI**: Beautiful Interface powered by `CustomTkinter` for a sleek experience.
- **Git Ingestion**: Clone and merge remote Git repositories directly via URLs (supports branches, tags, and commits).
- **Directory Tree**: Prepend visual directory folder hierarchy trees using Unicode box characters.
- **Token Estimation**: Display files processed, size, and estimated tokens using `tiktoken` with fallback.
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
python main.py
```

### CLI Mode
Merge all files in a directory recursively:
```bash
python main.py path/to/source -r -o MyMergedFile.txt
```

Merge a remote Git repository:
```bash
python main.py https://github.com/octocat/Hello-World --git -o HelloMerged.txt
```

#### CLI Arguments:
- `directory`: The source directory or Git repository URL.
- `extension` (Optional): Filter by a specific file extension (e.g., `.py`).
- `-r`, `--recursive`: Search subdirectories recursively.
- `-o`, `--output`: Specify the output filename (saved in the `out/` folder).
- `--git`: Treat the directory argument as a remote Git repository URL.
- `--branch`: The branch to checkout.
- `--tag`: The tag to checkout.
- `--commit`: The commit hash to checkout.
- `--git-token`: GitHub PAT token for private repositories.
- `--no-tree`: Disable visual directory tree prepend.
- `--include`: Comma-separated list of relative files to selectively include.

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
flake8 main.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Miro Slezák**
