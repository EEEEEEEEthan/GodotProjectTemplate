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

call "%~dp0egent.bat" --test all %headlessFlag%
exit /b %errorlevel%
