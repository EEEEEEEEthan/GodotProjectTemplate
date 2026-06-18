param(
	[Parameter(Mandatory = $true)]
	[string]$TestName,
	[switch]$Headless,
	[int]$TimeoutSeconds = 120
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$engineExe = Join-Path $projectRoot ".engine\.engine.exe"
if (-not (Test-Path $engineExe)) {
	Write-Error "Engine not found: $engineExe"
	exit 1
}

$logFile = Join-Path $env:TEMP "engine-test-$PID.log"
$stderrFile = Join-Path $env:TEMP "engine-test-$PID.err"
Remove-Item $logFile, $stderrFile -ErrorAction SilentlyContinue

$errorPattern = "SCRIPT ERROR:|Parse Error:|ERROR: Failed"

function Read-CombinedOutput {
	return @(
		(Get-Content $logFile -Raw -ErrorAction SilentlyContinue)
		(Get-Content $stderrFile -Raw -ErrorAction SilentlyContinue)
	) -join ""
}

function Write-CombinedOutput {
	Get-Content $logFile, $stderrFile -ErrorAction SilentlyContinue | Write-Host
}

$engineArguments = @()
if ($Headless) {
	$engineArguments += "--headless"
}
$engineArguments += @("--autotest", $TestName)

$process = Start-Process `
	-FilePath $engineExe `
	-ArgumentList $engineArguments `
	-WorkingDirectory $projectRoot `
	-NoNewWindow `
	-PassThru `
	-RedirectStandardOutput $logFile `
	-RedirectStandardError $stderrFile

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)

while (-not $process.HasExited) {
	if ((Get-Date) -gt $deadline) {
		Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
		Write-Host "Engine test timed out after ${TimeoutSeconds}s"
		Write-CombinedOutput
		Remove-Item $logFile, $stderrFile -ErrorAction SilentlyContinue
		exit 1
	}

	$combinedOutput = Read-CombinedOutput
	if ($combinedOutput -match $errorPattern) {
		Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
		Write-CombinedOutput
		Remove-Item $logFile, $stderrFile -ErrorAction SilentlyContinue
		exit 1
	}

	Start-Sleep -Milliseconds 200
}

$process.WaitForExit() | Out-Null
$exitCode = $process.ExitCode
$combinedOutput = Read-CombinedOutput
Write-CombinedOutput
Remove-Item $logFile, $stderrFile -ErrorAction SilentlyContinue

if ($combinedOutput -match $errorPattern) {
	exit 1
}

exit $exitCode
