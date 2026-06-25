# Text File Merger - Progress Checklist

- [x] Create `src/collector.py` (Pre-scan logic)
- [x] Optimise ignore filters in `src/filters.py` (pre-computed extensions tuple, cached regex gitignore rules)
- [x] Implement event-based cancellation (`threading.Event`) and sub-process helper in `src/merger.py`
- [x] Implement Parallel Text Merging with thread pool in `src/merger.py`
- [x] Implement Streaming for large files in `src/merger.py`
- [x] Implement Atomic output (.tmp file and os.replace) in `src/merger.py`
- [x] Implement Batch LibreOffice conversion in `src/pdf_utils.py` (orchestrated in merger.py)
- [x] Implement Parallel PDF conversion (fpdf2) in `src/pdf_utils.py`
- [x] Implement Memory-efficient PDF merging (batching) in `src/pdf_utils.py`
- [x] Implement GUI responsiveness improvements (`ProgressThrottler`) and cancellation in `src/gui.py`
- [x] Add performance tuning options to `src/config.py` and `config.json`
- [x] Write unit and integration tests and verify correctness
- [x] Update `CHANGELOG.md`, `README.md`, and `docs/documentation.md`
