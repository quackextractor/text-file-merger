@echo off
set VENV_DIR=venv

:: Check if virtual environment exists
if not exist %VENV_DIR% (
    echo Creating virtual environment...
    python -m venv %VENV_DIR%
    
    echo Activating environment and installing dependencies...
    call %VENV_DIR%\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
) else (
    echo Virtual environment found. Activating...
    call %VENV_DIR%\Scripts\activate
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
)

:: Setup and run pre-commit
echo.
echo Setting up pre-commit hooks...
pre-commit install

echo Running pre-commit checks on all files...
pre-commit run --all-files

:: Launch the script
echo Starting Merge Tool...
python merge_texts.py

:: Deactivate on close
call %VENV_DIR%\Scripts\deactivate
pause