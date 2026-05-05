param(
    [string]$Url = "http://127.0.0.1:8000/api/inngest",
    [string]$WatchPath = (Resolve-Path "$PSScriptRoot\..").Path,
    [int]$DebounceMs = 800
)

$ErrorActionPreference = "Stop"

$script:inngestProcess = $null
$script:lastRestart = Get-Date "2000-01-01"

function Test-ShouldRestart {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }

    $relative = $Path.Substring($WatchPath.Length).TrimStart("\", "/")
    $ignoredPrefixes = @(".git\", ".venv\", "__pycache__\", ".pytest_cache\")

    foreach ($prefix in $ignoredPrefixes) {
        if ($relative.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $false
        }
    }

    $ignoredExtensions = @(".log", ".pyc", ".tmp", ".swp")
    if ($ignoredExtensions -contains [System.IO.Path]::GetExtension($Path)) {
        return $false
    }

    return $true
}

function Stop-Inngest {
    if ($null -eq $script:inngestProcess -or $script:inngestProcess.HasExited) {
        return
    }

    Write-Host "Stopping Inngest Dev Server (PID $($script:inngestProcess.Id))..."
    taskkill.exe /PID $script:inngestProcess.Id /T /F | Out-Null
    $script:inngestProcess = $null
}

function Start-Inngest {
    Write-Host "Starting Inngest Dev Server for $Url"

    $processInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $processInfo.FileName = "npx.cmd"
    $processInfo.WorkingDirectory = $WatchPath
    $processInfo.UseShellExecute = $false
    $processInfo.ArgumentList.Add("--yes")
    $processInfo.ArgumentList.Add("--ignore-scripts=false")
    $processInfo.ArgumentList.Add("inngest-cli@latest")
    $processInfo.ArgumentList.Add("dev")
    $processInfo.ArgumentList.Add("-u")
    $processInfo.ArgumentList.Add($Url)
    $processInfo.ArgumentList.Add("--no-discovery")

    $script:inngestProcess = [System.Diagnostics.Process]::Start($processInfo)
    $script:lastRestart = Get-Date
}

function Restart-Inngest {
    param([string]$ChangedPath)

    $now = Get-Date
    if (($now - $script:lastRestart).TotalMilliseconds -lt $DebounceMs) {
        return
    }

    Write-Host "Change detected: $ChangedPath"
    Stop-Inngest
    Start-Sleep -Milliseconds 300
    Start-Inngest
}

$watcher = [System.IO.FileSystemWatcher]::new($WatchPath)
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true
$watcher.NotifyFilter = [System.IO.NotifyFilters]"FileName, DirectoryName, LastWrite"

$action = {
    $path = $Event.SourceEventArgs.FullPath
    if (Test-ShouldRestart $path) {
        Restart-Inngest $path
    }
}

$subscriptions = @(
    Register-ObjectEvent $watcher Changed -Action $action,
    Register-ObjectEvent $watcher Created -Action $action,
    Register-ObjectEvent $watcher Deleted -Action $action,
    Register-ObjectEvent $watcher Renamed -Action $action
)

try {
    Write-Host "Watching $WatchPath"
    Write-Host "Open the Inngest UI at http://127.0.0.1:8288"
    Start-Inngest

    while ($true) {
        Start-Sleep -Seconds 1
        if ($null -ne $script:inngestProcess -and $script:inngestProcess.HasExited) {
            Write-Host "Inngest Dev Server exited with code $($script:inngestProcess.ExitCode). Restarting..."
            Start-Inngest
        }
    }
}
finally {
    Stop-Inngest
    foreach ($subscription in $subscriptions) {
        Unregister-Event -SubscriptionId $subscription.Id -ErrorAction SilentlyContinue
    }
    $watcher.Dispose()
}
