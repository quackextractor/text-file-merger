# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [1.7.0] - 2026-07-02
### Added
* **Selective Include Mode**: Added selective include filter (`--include` in CLI, "Selective Mode" checkbox/input in GUI) to allow merging only specified files by their relative paths.
* **Scrollable GUI Container**: Upgraded the main GUI container to a `CTkScrollableFrame` to permanently prevent window overflow.
### Removed
* **Redundant skip_css Option**: Removed dedicated `skip_css_if_no_ext` config option, checkbox, and collector parameter, as extension filtering is fully configurable in Settings.

## [1.6.1] - 2026-06-25
### Added
* **Preview Ingestion Stats**: Enabled token estimation inside dry-run preview mode.
* **Compact Summary Panel**: Created a side-by-side split layout panel in the GUI to show files, size, tokens, and output path dynamically, replacing pop-up modal dialogs.
### Fixed
* **URL Source Directory Bypass**: Fixed an issue where remote repository URLs inputted in the GUI triggered local directory checks and caused validation errors.
* **Token Rounding Format**: Formatted estimated token counts in thousands (e.g., `29.3k` instead of raw integers).

## [1.6.0] - 2026-06-25
### Added
* **Token Counting**: Integrated `tiktoken` for accurate token estimation with fallback to character count estimation (`len // 4`). Shows number of files, total size, and token counts upon merge completion.
* **Git Ingestion**: Added the ability to clone and merge directly from remote Git URLs, supporting branch, tag, or commit ref checkouts, GITHUB_TOKEN PAT embedding, and automatic fallback to full clone.
* **Directory Tree Prepending**: Prepends a text-based visual folder hierarchy tree (Unicode box drawing) to text/PDF merges. Adjustable via CLI `--no-tree` and GUI checkbox.
* **UI Expansion**: Expanded GUI window size to support Git Repository toggle controls, Branch/Token entries, and a read-only visual Directory Structure tree textbox.

## [1.5.0] - 2026-06-25
### Added
* **Two-Phase Pipeline**: Implemented file pre-scanning (Phase 1) using a new `collect_files` module for accurate progress calculation, safe parallelization, and responsive cancellation.
* **Parallel Text Merging**: Accelerated merges using `ThreadPoolExecutor` for files under the performance threshold.
* **Streaming for Large Files**: Stream files exceeding 5MB directly using `shutil.copyfileobj` to prevent excessive RAM utilization.
* **Atomic Merges**: Merges now write to a `.tmp` file and perform an atomic `os.replace` on success, preventing corruption.
* **Batch LibreOffice Conversion**: Feeds multiple DOCX/DOC files into a single headless LibreOffice call for a massive speed boost.
* **Parallel PDF Fallback**: Plain text to PDF conversion is parallelized using processes/threads.
* **GUI Responsiveness**: Added `ProgressThrottler` to throttle progress bar updates and logs (flushed every 100ms), and replaced cancellation flags with standard thread-safe `threading.Event` objects.
* **Configurable Performance Settings**: Added performance settings block to `config.json` and `src/config.py` for advanced tuning.

## [1.4.0] - 2026-04-25
### Added
* **Source Text Preservation**: Added the ability to preserve individual parsed source text files during the merging process.
* **Interface Controls**: Introduced a `--keep-sources-txt` CLI argument and a corresponding "Keep source text files" checkbox in the GUI.
### Changed
* **Directory Structure**: Organized the output directory for kept source files. Preserved files are now cleanly separated into `out/<source-dir-name>/txt` and `out/<source-dir-name>/pdf` subdirectories.
* **GUI Layout**: Positioned the "Keep source text files" checkbox independently from the PDF options to accurately reflect that text extraction functions independently of PDF compilation.

## [1.3.0] - 2026-04-24
### Added
* **Word Document Support**: Added support for processing modern `.docx` and legacy `.doc` files.
* **PDF Conversion Tiers**: Implemented multi-tier PDF conversion for Word documents, attempting conversion via `docx2pdf` first, followed by LibreOffice Headless, and falling back to raw text extraction if necessary.
* **Styled PDF Formatting**: Introduced a `--styled-pdf` CLI argument and a GUI checkbox to apply modern formatting and Helvetica fonts to the output PDF.
* **Unicode Font Support**: Implemented system font detection for Windows, macOS, and Linux to load standard monospaced Unicode TTF fonts for unstyled PDF exports.
* **Dependencies**: Added `python-docx` and `docx2pdf` to the `requirements.txt` file.

## [1.2.0] - 2026-04-24
### Changed
* **Architecture Refactor**: Split the monolithic `merge_texts.py` into a modular package structure within a new `src/` directory (`config.py`, `filters.py`, `pdf_utils.py`, `merger.py`, and `gui.py`).
* **Entry Point**: Established `main.py` at the project root as the new primary entry point for both GUI and CLI operations.
* **Test Suite**: Updated `tests/test_merger.py` to reflect the new package imports and isolated module testing.
* **CI/CD Pipeline**: Updated PyInstaller build steps in the GitHub Actions workflow (`python-app.yml`) to target `main.py` for executable generation.

## [1.1.8] - 2026-04-23
### Added
* **Improved Release description**: Added a workflow step to extract the current version section from CHANGELOG.md into release_notes.md and pass it as the release body (body_path) when creating a GitHub release.
* **PDF Support**: Added PDF compilation features, NotebookLM formatting, GUI checkboxes, and CLI arguments.
* **Dependencies**: Added `fpdf2` and `pypdf` packages to the requirements list.
* **Settings Options**: Added the explicit "Ignored Files" text box and the "Reload from File" button to the GUI settings menu.
* **Settings Interface**: Improved the settings window layout and added the temporary session changes toggle.
* **Directory Navigation**: Improved the output directory button to open the folder directly instead of selecting the newly created file in the system file explorer.

## [1.1.7] - 2026-03-25
### Added
* **Quick Access Buttons**: Added "Open Folder" buttons for both Source and Output directories to improve workflow efficiency.
* **Cross-Platform Support**: Implemented native folder opening logic for Windows, macOS, and Linux.
* **Improved Validation**: Added check to verify folder existence before attempting to open, providing log feedback if the path is missing.

## [1.1.6] - 2026-03-18
Add .gitignore support and UI/CLI toggle

## [1.1.5] - 2026-03-18

## Fixed
Use current path as initialdir for directory dialogs

## [1.1.4] - 2026-03-18

## Fixed
Added proper loading bar

## [1.1.3] - 2026-03-18

## Fixed
Include and load bundled config.json for build

## [1.1.2] - 2026-03-18

### Fixed
* **UI Layout**: Added proper vertical padding (`pady`) to all form labels and inputs to resolve cramped visual spacing.
* **UI Colors**: Muted the bright red "Cancel" button to better match the CustomTkinter dark theme aesthetic.

## [1.1.1] - 2026-03-17

### Fixed
* **CI Test Failure**: Resolved `ModuleNotFoundError` in GitHub Actions by correctly setting `PYTHONPATH`.
* **Code Complexity**: Refactored `merge_files` to reduce cyclomatic complexity (C901) and meeting linting standards.
* **Linting**: Fixed long line (E501) violations in `merge_texts.py`.

## [1.1.0] - 2026-03-17

### Added
* Integrated **CustomTkinter** for a modern, sleek GUI theme.
* **Background Threading** to prevent UI freezing during large file merges.
* **Progress Indicator** with an indeterminate progress bar.
* **Inline Status Log** as a scrollable text area for non-blocking feedback.
* **Output Directory Selector** in the GUI for easier file destination management.
* **Target Extensions Filter** directly in the GUI.
* **Source Directory History** in a combo box that remembers last used folders.
* **File Preview Panel** (Dry Run) to see files before merging.
* **In-App Settings Editor** for managing ignored directories and extensions.
* **Cancel Operation Button** for safe interruption of background tasks.
* **Drag & Drop Visual Feedback** (highlighting source field on hover).
* **Tooltips** for various GUI elements to improve user guidance.
* Expanded test suite with unit, integration, and logic tests.

### Fixed
* Multiple flake8 linting violations (E302, E501, W292, W293).
* Missing blank lines between classes and functions in `merge_texts.py`.
* Closing brace issue in `DEFAULT_CONFIG`.

## [1.0.0] - 2026-03-17

### Added
* Initial release of the Text File Merger utility.
* Graphical User Interface (GUI) with Drag & Drop support.
* Command Line Interface (CLI) for batch processing.
* Configurable ignore lists for files, directories, and extensions.
* History tracking for output filenames.
* Custom output directory support.
* MIT License.
* GitHub Actions workflow for CI/CD.
* Unit and linting tests.
