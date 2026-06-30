param(
	[Parameter(Mandatory = $true, Position = 0)]
	[string]$TestName,
	[switch]$Headless
)

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$egentBat = Join-Path $projectRoot "egent.bat"
$arguments = @("--test", $TestName)
if ($Headless) {
	$arguments += "--headless"
}

& $egentBat @arguments
exit $LASTEXITCODE
