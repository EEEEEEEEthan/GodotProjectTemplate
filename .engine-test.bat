@echo off
setlocal

set "ignorePrepare=0"
set "headless=0"
set "testName="

:parse_args
if "%~1"=="" goto :args_done
if "%~1"=="--ignore-prepare" (
    set "ignorePrepare=1"
    shift
    goto :parse_args
)
if "%~1"=="--headless" (
    set "headless=1"
    shift
    goto :parse_args
)
if "%testName%"=="" (
    set "testName=%~1"
    shift
    goto :parse_args
)
shift
goto :parse_args

:args_done
if "%testName%"=="" (
    echo Usage: .engine-test.bat [--headless] TESTNAME
    exit /b 1
)

if "%ignorePrepare%"=="0" (
    call .engine-prepare.bat
    if errorlevel 1 exit /b 1
    if "%headless%"=="1" (
        .\.engine\.engine.exe --headless --import
    ) else (
        .\.engine\.engine.exe --import
    )
    if errorlevel 1 exit /b 1
)

if "%headless%"=="1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0.engine-test-run.ps1" -TestName "%testName%" -Headless
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0.engine-test-run.ps1" -TestName "%testName%"
)
exit /b %ERRORLEVEL%
