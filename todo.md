# Progress Tracker

## Phase 1: Dependencies & Configuration
- [x] Add `tiktoken>=0.7.0` and `gitpython>=3.1.0` to `requirements.txt`
- [x] Add `"include_tree": true` configuration to `config.json`
- [x] Update `src/config.py` default config with `include_tree` default

## Phase 2: Feature Utilities
- [x] Implement `src/token_utils.py` for token estimation and fallback character counting
- [x] Implement `src/git_utils.py` for shallow cloning, checkout of branches/tags/commits, and token handling
- [x] Implement `src/tree_utils.py` for directory tree view generation

## Phase 3: Core Integration
- [x] Update `src/merger.py` to support Git cloning, tree inclusion, and token calculation
- [x] Update CLI (`main.py`) to support Git flags, tree toggle, and summary statistics printing
- [x] Update GUI (`src/gui.py`) to support Git options, tree view toggle, and output tree box

## Phase 4: Verification & Testing
- [x] Write unit & integration tests in `tests/test_gitingest_features.py`
- [x] Verify test suite passes successfully
- [x] Manually test CLI and GUI operations

## Phase 5: Documentation & Versioning
- [x] Update `CHANGELOG.md`
- [x] Update `README.md`
- [x] Update `docs/documentation.md`
