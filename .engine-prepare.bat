@echo off
setlocal enabledelayedexpansion

REM Version definition
set "useMono=0"
set "versionNumber=4.7"
set "flavor=beta3"
set "tmpDir=.tmp"
set "engineDir=.engine"
set "zipFile=%tmpDir%\godot.zip"

if not "%useMono%"=="0" (
    set "zipSlug=mono_win64.zip"
    set "godotExeFile=Godot_v%versionNumber%-%flavor%_mono_win64.exe"
) else (
    set "zipSlug=win64.exe.zip"
    set "godotExeFile=Godot_v%versionNumber%-%flavor%_win64.exe"
)
set "engineExe=%engineDir%\%godotExeFile%"

REM 1. Check if engine exists
if exist "%engineExe%" (
    echo Engine already exists, skipping download
    goto :create_symlink
)

REM 2. Remove old engine folder
if exist "%engineDir%" (
    echo Removing old engine folder...
    rmdir /s /q "%engineDir%"
)

REM 3. Download engine to .tmp/
echo Creating temp directory...
if not exist "%tmpDir%" mkdir "%tmpDir%"

echo Downloading engine %versionNumber%...
powershell -NoProfile -ExecutionPolicy Bypass -Command "& {$v='%versionNumber%'; $f='%flavor%'; $s='%zipSlug%'; $u='https://downloads.godotengine.org/?version='+$v+'&flavor='+$f+'&slug='+$s+'&platform=windows.64'; Invoke-WebRequest -Uri $u -OutFile '%zipFile%'}"
if errorlevel 1 (
    echo Download failed
    exit /b 1
)

REM 4. Extract to temp directory first
echo Extracting engine...
set "extractDir=%tmpDir%\extract"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& {Expand-Archive -Path '%zipFile%' -DestinationPath '%extractDir%' -Force}"
if errorlevel 1 (
    echo Extraction failed
    exit /b 1
)

REM Find and copy files from extracted folder to .engine
echo Moving files to .engine directory...
if not exist "%engineDir%" mkdir "%engineDir%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& {$extractDir='%extractDir%'; $engineDir='%engineDir%'; $exeName='%godotExeFile%'; $foundExe=Get-ChildItem -Path $extractDir -Recurse -Filter $exeName | Select-Object -First 1; if ($foundExe) { $sourceDir=$foundExe.Directory.FullName; Get-ChildItem -Path $sourceDir | Copy-Item -Destination $engineDir -Recurse -Force } else { Write-Host 'Engine exe not found'; exit 1 }}"
if errorlevel 1 (
    echo Failed to move files
    exit /b 1
)

REM 5. Remove .tmp/
echo Cleaning temp files...
rmdir /s /q "%tmpDir%"

:create_symlink
REM Create .engine.exe hard link
if not exist "%engineExe%" (
    echo Engine exe not found: %engineExe%
    exit /b 1
)
echo Creating .engine.exe hard link...
if exist "%engineDir%\.engine.exe" del "%engineDir%\.engine.exe"
mklink /h "%engineDir%\.engine.exe" "%engineExe%"

echo Engine preparation completed!
endlocal
