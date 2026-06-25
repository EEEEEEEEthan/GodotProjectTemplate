@echo off
setlocal enabledelayedexpansion

set "anyFailed=0"
set "headlessFlag="

:parse_args
if "%~1"=="" goto :args_done
if "%~1"=="--headless" (
    set "headlessFlag=-Headless"
    shift
    goto :parse_args
)
shift
goto :parse_args

:args_done

call .engine-prepare.bat
if errorlevel 1 exit /b 1

.\.engine\.engine.exe --headless --import
if errorlevel 1 exit /b 1

REM Registered test names; keep in sync with the autotest node
for %%t in (hellotest offsidetest) do (
    echo === Running test: %%t ===
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0.engine-test.ps1" -TestName %%t -IgnorePrepare %headlessFlag%
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
