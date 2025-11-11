# MonDashboard - Development Run Script (Windows)
# Starts Chrome with CDP and Flask app with unified logging

Write-Host "=== MonDashboard Dev Mode ===" -ForegroundColor Cyan

# Set environment variables
$env:ENV="dev"
$env:CONSOLE_BRIDGE_MODE="cdp"  # cdp|inpage|off
$env:CDP_PORT="9222"
$env:LOG_LEVEL="INFO"

# Find Chrome executable
$chromePaths = @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chromeExe = $null
foreach ($path in $chromePaths) {
    if (Test-Path $path) {
        $chromeExe = $path
        break
    }
}

if ($chromeExe) {
    Write-Host "[CDP] Starting Chrome with remote debugging..." -ForegroundColor Green
    Write-Host "      Path: $chromeExe" -ForegroundColor Gray
    Write-Host "      Port: $env:CDP_PORT" -ForegroundColor Gray
    
    # Start Chrome in background
    Start-Process $chromeExe -ArgumentList @(
        "--remote-debugging-port=$env:CDP_PORT",
        "--user-data-dir=$env:TEMP\chrome-dev-profile"
    ) -WindowStyle Hidden
    
    Write-Host "[CDP] Chrome started. Waiting 2 seconds..." -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    Write-Host "[CDP] Chrome not found. CDP mode will not be available." -ForegroundColor Yellow
    Write-Host "      Install Chrome or use CONSOLE_BRIDGE_MODE=inpage" -ForegroundColor Yellow
}

# Start Flask app
Write-Host "[Flask] Starting application..." -ForegroundColor Green
python .\run.pyw

Write-Host "=== MonDashboard Stopped ===" -ForegroundColor Cyan
