@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "ROOT=%%~fI"
set "VENV_DIR=%ROOT%\.venv"
set "DRY_RUN=0"

if /I "%~1"=="--help" goto :help
if /I "%~1"=="-h" goto :help
if /I "%~1"=="--dry-run" set "DRY_RUN=1"
if /I "%~1"=="-n" set "DRY_RUN=1"
if not "%~1"=="" if /I not "%~1"=="--dry-run" if /I not "%~1"=="-n" if /I not "%~1"=="--help" if /I not "%~1"=="-h" (
    echo Unknown option "%~1"
    echo.
    goto :help
)

set /a removed_dirs=0
set /a removed_files=0

echo Cleaning generated artifacts under "%ROOT%"
if "%DRY_RUN%"=="1" echo Dry-run mode enabled. Nothing will be deleted.

for %%D in (
    ".pytest_cache"
    ".ruff_cache"
    ".mypy_cache"
    ".pytest_tmp"
    "test_tmp"
    "build"
    "dist"
    "htmlcov"
    "examples\output"
) do (
    call :remove_dir "%ROOT%\%%~D"
)

for /d /r "%ROOT%" %%D in (__pycache__) do call :remove_dir "%%~fD"
for /d /r "%ROOT%" %%D in (*.egg-info) do call :remove_dir "%%~fD"

call :remove_file "%ROOT%\.coverage"
call :remove_file "%ROOT%\coverage.xml"

for /r "%ROOT%" %%F in (*.pyc) do call :remove_file "%%~fF"
for /r "%ROOT%" %%F in (*.pyo) do call :remove_file "%%~fF"

echo.
echo Removed !removed_dirs! directorie(s) and !removed_files! file(s).
exit /b 0

:remove_dir
set "TARGET=%~f1"
if not exist "%TARGET%" exit /b 0

call :is_in_venv "%TARGET%"
if "%ERRORLEVEL%"=="0" exit /b 0

if "%DRY_RUN%"=="1" (
    echo [dry-run] Removing directory "%TARGET%"
    set /a removed_dirs+=1
    exit /b 0
)

rmdir /s /q "%TARGET%" 2>nul
if exist "%TARGET%" (
    echo Warning: could not remove directory "%TARGET%"
    exit /b 0
)

echo Removed directory "%TARGET%"
set /a removed_dirs+=1
exit /b 0

:remove_file
set "TARGET=%~f1"
if not exist "%TARGET%" exit /b 0

call :is_in_venv "%TARGET%"
if "%ERRORLEVEL%"=="0" exit /b 0

if "%DRY_RUN%"=="1" (
    echo [dry-run] Removing file "%TARGET%"
    set /a removed_files+=1
    exit /b 0
)

del /f /q "%TARGET%" 2>nul
if exist "%TARGET%" (
    echo Warning: could not remove file "%TARGET%"
    exit /b 0
)

echo Removed file "%TARGET%"
set /a removed_files+=1
exit /b 0

:is_in_venv
set "TARGET=%~f1"
if /I "%TARGET%"=="%VENV_DIR%" exit /b 0

set "PREFIX=%VENV_DIR%\"
set "TRIMMED=!TARGET:%PREFIX%=!"
if /I not "!TRIMMED!"=="!TARGET!" exit /b 0

exit /b 1

:help
echo Usage: clean.bat [--dry-run]
echo.
echo Removes common Python cache and temporary artifacts from this repository
echo without touching ".venv".
exit /b 0
