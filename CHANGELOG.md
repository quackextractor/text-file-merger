# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2026-03-18

### Fixed
- **UI Layout**: Added proper vertical padding (`pady`) to all form labels and inputs to resolve cramped visual spacing.
- **UI Colors**: Muted the bright red "Cancel" button to better match the CustomTkinter dark theme aesthetic.

## [1.1.1] - 2026-03-17

### Fixed
- **CI Test Failure**: Resolved `ModuleNotFoundError` in GitHub Actions by correctly setting `PYTHONPATH`.
- **Code Complexity**: Refactored `merge_files` to reduce cyclomatic complexity (C901) and meeting linting standards.
- **Linting**: Fixed long line (E501) violations in `merge_texts.py`.

## [1.1.0] - 2026-03-17

### Added
- Integrated **CustomTkinter** for a modern, sleek GUI theme.
- **Background Threading** to prevent UI freezing during large file merges.
- **Progress Indicator** with an indeterminate progress bar.
- **Inline Status Log** as a scrollable text area for non-blocking feedback.
- **Output Directory Selector** in the GUI for easier file destination management.
- **Target Extensions Filter** directly in the GUI.
- **Source Directory History** in a combo box that remembers last used folders.
- **File Preview Panel** (Dry Run) to see files before merging.
- **In-App Settings Editor** for managing ignored directories and extensions.
- **Cancel Operation Button** for safe interruption of background tasks.
- **Drag & Drop Visual Feedback** (highlighting source field on hover).
- **Tooltips** for various GUI elements to improve user guidance.
- Expanded test suite with unit, integration, and logic tests.

### Fixed
- Multiple flake8 linting violations (E302, E501, W292, W293).
- Missing blank lines between classes and functions in `merge_texts.py`.
- Closing brace issue in `DEFAULT_CONFIG`.

## [1.0.0] - 2026-03-17

### Added
- Initial release of the Text File Merger utility.
- Graphical User Interface (GUI) with Drag & Drop support.
- Command Line Interface (CLI) for batch processing.
- Configurable ignore lists for files, directories, and extensions.
- History tracking for output filenames.
- Custom output directory support.
- MIT License.
- GitHub Actions workflow for CI/CD.
- Unit and linting tests.
