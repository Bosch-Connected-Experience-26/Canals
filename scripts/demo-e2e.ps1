param(
    [string] $OrchestratorUrl = "http://localhost:8001",
    [string] $JourneyId = "demo-trip"
)

$ErrorActionPreference = "Stop"

$Vehicle = @{
    batteryPercent = 34
    rangeKm = 145
    lat = 52.52
    lng = 13.405
    connector = "CCS"
}

function Invoke-JsonPost {
    param(
        [string] $Path,
        [hashtable] $Body
    )

    Invoke-RestMethod `
        -Method Post `
        -Uri "$OrchestratorUrl$Path" `
        -ContentType "application/json" `
        -Body ($Body | ConvertTo-Json -Depth 10)
}

function Invoke-CommandDemo {
    param(
        [string] $Transcript,
        [bool] $Online = $true
    )

    Write-Host ""
    Write-Host "User: $Transcript" -ForegroundColor Cyan

    $response = Invoke-JsonPost "/command" @{
        journeyId = $JourneyId
        transcript = $Transcript
        network = @{
            online = $Online
            latencyMs = $(if ($Online) { 80 } else { $null })
        }
        vehicle = $Vehicle
    }

    Write-Host "Route: $($response.route)"
    Write-Host "Intent: $($response.intent)"
    Write-Host "Cloud used: $($response.debug.cloudUsed)"
    if ($response.selectedStation) {
        Write-Host "Station: $($response.selectedStation.name)"
    }
    if ($response.actions.Count -gt 0) {
        Write-Host "Action: $($response.actions[0].type)"
    }
    if ($response.debug.warnings.Count -gt 0) {
        Write-Host "Warnings: $($response.debug.warnings -join '; ')" -ForegroundColor Yellow
    }
    Write-Host "Assistant: $($response.spokenResponse)" -ForegroundColor Green
}

Write-Host "Checking orchestrator health..." -ForegroundColor Cyan
$health = Invoke-RestMethod "$OrchestratorUrl/health"
Write-Host "Health: $($health.status), cache=$($health.cacheBackend), cloud=$($health.cloudBackend)"

Write-Host ""
Write-Host "Starting journey cache..." -ForegroundColor Cyan
$journey = Invoke-JsonPost "/journey/start" @{ journeyId = $JourneyId }
Write-Host $journey.message

Invoke-CommandDemo "Find a fast charger with coffee" $true
Invoke-CommandDemo "Check live availability" $true
Invoke-CommandDemo "Is it available right now?" $false
Invoke-CommandDemo "Navigate there" $false
Invoke-CommandDemo "Turn the lights off" $false
Invoke-CommandDemo "Turn the lights on" $false
