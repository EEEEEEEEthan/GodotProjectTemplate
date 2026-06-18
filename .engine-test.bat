@echo off
setlocal

set "ignorePrepare=0"
set "testName="

if "%~1"=="--ignore-prepare" (
    set "ignorePrepare=1"
    set "testName=%~2"
) else (
    set "testName=%~1"
)

if "%testName%"=="" (
    echo Usage: .engine-test.bat TESTNAME
    exit /b 1
)

if "%ignorePrepare%"=="0" (
    call .engine-prepare.bat
    if errorlevel 1 exit /b 1
    .\.engine\.engine.exe --headless --import
    if errorlevel 1 exit /b 1
)

.\.engine\.engine.exe --autotest "%testName%"
exit /b %ERRORLEVEL%
