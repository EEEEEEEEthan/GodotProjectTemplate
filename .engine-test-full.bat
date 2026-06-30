@echo off
setlocal enabledelayedexpansion

set "headlessFlag="

:parse_args
if "%~1"=="" goto :args_done
if "%~1"=="--headless" (
    set "headlessFlag=--headless"
    shift
    goto :parse_args
)
shift
goto :parse_args

:args_done

set "anyFailed=0"
for %%t in (
    egent_handlers/tests/hello_test.gd
) do (
    echo === Running test: %%t ===
    call "%~dp0egent.bat" --test %%t %headlessFlag%
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
