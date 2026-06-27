param(
    [string]$BackendBaseUrl = "http://127.0.0.1:8009",
    [string]$EnvPath = "backend\.env"
)

$ErrorActionPreference = "Stop"

function Read-EnvValue {
    param([string]$Path, [string]$Name)

    if (!(Test-Path $Path)) {
        throw "Env file not found: $Path"
    }

    $line = Get-Content $Path | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
    if (!$line) {
        return ""
    }

    return $line.Substring($Name.Length + 1).Trim()
}

function Test-Url {
    param(
        [string]$Label,
        [string]$Url,
        [int[]]$ExpectedStatusCodes
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 8 -ErrorAction Stop
        $statusCode = [int]$response.StatusCode
        $content = [string]$response.Content
    } catch {
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
            $content = $reader.ReadToEnd()
        } else {
            Write-Host "[FAIL] $Label -> $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }

    if ($ExpectedStatusCodes -contains $statusCode) {
        if ($content -match "Tunnel .* not found") {
            Write-Host "[FAIL] $Label -> tunnel exists in config, but NATAPP client is not online" -ForegroundColor Red
            return $false
        }

        Write-Host "[ OK ] $Label -> HTTP $statusCode" -ForegroundColor Green
        return $true
    }

    Write-Host "[FAIL] $Label -> HTTP $statusCode" -ForegroundColor Red
    if ($content) {
        Write-Host $content
    }
    return $false
}

$redirectUri = Read-EnvValue -Path $EnvPath -Name "WECHAT_REDIRECT_URI"
if (!$redirectUri) {
    throw "WECHAT_REDIRECT_URI is empty in $EnvPath"
}

Write-Host "Wechat redirect URI: $redirectUri"
Write-Host "Expected NATAPP target: 127.0.0.1:8009"
Write-Host ""

$healthOk = Test-Url -Label "local backend health" -Url "$BackendBaseUrl/health" -ExpectedStatusCodes @(200)
$localCallbackOk = Test-Url -Label "local wechat callback route" -Url "$BackendBaseUrl/api/auth/wechat/callback" -ExpectedStatusCodes @(422)

$separator = if ($redirectUri.Contains("?")) { "&" } else { "?" }
$publicProbeUrl = "$redirectUri${separator}code=probe&state=probe"
$publicCallbackOk = Test-Url -Label "public NATAPP callback" -Url $publicProbeUrl -ExpectedStatusCodes @(400)

Write-Host ""
if ($healthOk -and $localCallbackOk -and $publicCallbackOk) {
    Write-Host "Wechat tunnel check passed. Refresh the login page and scan again." -ForegroundColor Green
    exit 0
}

Write-Host "Wechat tunnel check failed." -ForegroundColor Red
Write-Host "Make sure NATAPP is running and the tunnel target is 127.0.0.1:8009."
exit 1
