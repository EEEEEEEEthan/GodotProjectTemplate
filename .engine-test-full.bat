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

REM Auto-discover test names from tests/*_test.gd
for %%f in (tests\*_test.gd) do (
    set "filename=%%~nf"
    set "testname=!filename:_test=!"
    echo === Running test: !testname! ===
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0.engine-test.ps1" -TestName !testname! -IgnorePrepare %headlessFlag%
    if errorlevel 1 (
        echo [FAILED] !testname!
        set "anyFailed=1"
    ) else (
        echo [PASSED] !testname!
    )
)

if "!anyFailed!"=="1" (
    echo Some tests failed
    exit /b 1
)

echo All tests passed
exit /b 0
