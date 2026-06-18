@echo off
setlocal enabledelayedexpansion

set "anyFailed=0"

call .engine-prepare.bat
if errorlevel 1 exit /b 1

.\.engine\.engine.exe --headless --import
if errorlevel 1 exit /b 1

REM Registered test names; keep in sync with the autotest node
for %%t in () do (
    echo === Running test: %%t ===
    call .engine-test.bat --ignore-prepare %%t
    if errorlevel 1 (
        echo [FAILED] %%t
        set "anyFailed=1"
    ) else (
        echo [PASSED] %%t
    )
)

if "!anyFailed!"=="1" (
    echo Some tests failed
    exit /b 1
)

echo All tests passed
exit /b 0
