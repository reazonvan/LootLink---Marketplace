param(
    [string]$Domain = "lootlink.ru",
    [string]$WwwDomain = "www.lootlink.ru"
)

$ErrorActionPreference = "Stop"

function Test-Status {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Expected
    )

    $result = curl.exe -sS -L -o NUL -w "%{http_code}" --max-time 20 $Url
    $ok = $result -eq $Expected
    $status = if ($ok) { "OK" } else { "FAIL" }
    Write-Host ("[{0}] {1}: got {2}, expected {3} ({4})" -f $status, $Name, $result, $Expected, $Url)
    return $ok
}

function Test-RedirectPrefix {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$ExpectedStatus,
        [Parameter(Mandatory = $true)][string]$ExpectedLocationPrefix
    )

    $headers = curl.exe -sS -I --max-time 20 $Url
    $statusLine = ($headers | Select-String -Pattern "^HTTP/" | Select-Object -First 1).Line
    $locationLine = ($headers | Select-String -Pattern "^Location:" | Select-Object -First 1).Line
    $statusCode = ($statusLine -split " ")[1]
    $location = if ($locationLine) { $locationLine.Substring(9).Trim() } else { "" }

    $ok = ($statusCode -eq $ExpectedStatus) -and $location.StartsWith($ExpectedLocationPrefix)
    $state = if ($ok) { "OK" } else { "FAIL" }
    Write-Host ("[{0}] {1}: status={2}, location={3}" -f $state, $Name, $statusCode, $location)
    return $ok
}

function Test-Contains {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Pattern
    )

    $body = curl.exe -sS --max-time 20 $Url
    $ok = $body -match $Pattern
    $state = if ($ok) { "OK" } else { "FAIL" }
    Write-Host ("[{0}] {1}: pattern '{2}' in {3}" -f $state, $Name, $Pattern, $Url)
    return $ok
}

function Test-AuthSmoke {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUrl
    )

    $loginCookies = Join-Path $PSScriptRoot "smoke_login.cookies"
    $regCookies = Join-Path $PSScriptRoot "smoke_register.cookies"

    try {
        $null = curl.exe -sS -c $loginCookies --max-time 20 "$BaseUrl/accounts/login/"
        $csrfLine = Get-Content $loginCookies | Select-String "lootlink_csrftoken" | Select-Object -Last 1
        $csrf = ($csrfLine -split "\s+")[-1]
        $loginCode = curl.exe -sS -o NUL -w "%{http_code}" -b $loginCookies -c $loginCookies `
            -e "$BaseUrl/accounts/login/" --max-time 20 -X POST "$BaseUrl/accounts/login/" `
            -d "csrfmiddlewaretoken=$csrf&username=__smoke_invalid__&password=__smoke_invalid__"
        $loginOk = $loginCode -eq "200"
        Write-Host ("[{0}] AUTH login invalid POST -> {1}" -f ($(if ($loginOk) { "OK" } else { "FAIL" }), $loginCode))

        $null = curl.exe -sS -c $regCookies --max-time 20 "$BaseUrl/accounts/register/"
        $csrfLine2 = Get-Content $regCookies | Select-String "lootlink_csrftoken" | Select-Object -Last 1
        $csrf2 = ($csrfLine2 -split "\s+")[-1]
        $rand = Get-Random -Minimum 100000 -Maximum 999999
        $regCode = curl.exe -sS -o NUL -w "%{http_code}" -b $regCookies -c $regCookies `
            -e "$BaseUrl/accounts/register/" --max-time 20 -X POST "$BaseUrl/accounts/register/" `
            -d "csrfmiddlewaretoken=$csrf2&username=smoketest_$rand&email=smoketest_$rand@example.com&phone=+79990000000&password1=Password123!&password2=Mismatch123!"
        $regOk = $regCode -eq "200"
        Write-Host ("[{0}] AUTH register invalid POST -> {1}" -f ($(if ($regOk) { "OK" } else { "FAIL" }), $regCode))

        return ($loginOk -and $regOk)
    }
    finally {
        Remove-Item $loginCookies, $regCookies -ErrorAction SilentlyContinue
    }
}

$base = "https://$Domain"
$all = @()

# Public surface
$all += Test-Status -Name "Home" -Url "$base/" -Expected "200"
$all += Test-Status -Name "Catalog" -Url "$base/catalog/" -Expected "200"
$all += Test-Status -Name "Sitemap" -Url "$base/sitemap.xml" -Expected "200"
$all += Test-Status -Name "Robots" -Url "$base/robots.txt" -Expected "200"
$all += Test-Contains -Name "Robots has sitemap" -Url "$base/robots.txt" -Pattern "Sitemap:\s*https://lootlink\.ru/sitemap\.xml"
$all += Test-Status -Name "Manifest" -Url "$base/manifest.json" -Expected "200"
$all += Test-Status -Name "OG image" -Url "$base/static/images/og-image.jpg" -Expected "200"
$all += Test-RedirectPrefix -Name "WWW -> Canonical" -Url "https://$WwwDomain/anything" -ExpectedStatus "301" -ExpectedLocationPrefix "https://$Domain/anything"
$all += Test-RedirectPrefix -Name "HTTP -> HTTPS" -Url "http://$Domain/catalog/" -ExpectedStatus "308" -ExpectedLocationPrefix "https://$Domain/catalog/"

# SEO markup
$all += Test-Contains -Name "Canonical tag" -Url "$base/" -Pattern 'rel=\"canonical\"\s+href=\"https://lootlink\.ru/'
$all += Test-Contains -Name "Manifest link tag" -Url "$base/" -Pattern 'rel=\"manifest\"\s+href=\"/manifest\.json\"'
$all += Test-Contains -Name "SearchAction target q" -Url "$base/" -Pattern "https://lootlink\.ru/search/\?q=\{search_term_string\}"

# Auth smoke
$all += Test-Status -Name "Login GET" -Url "$base/accounts/login/" -Expected "200"
$all += Test-Status -Name "Register GET" -Url "$base/accounts/register/" -Expected "200"
$all += Test-AuthSmoke -BaseUrl $base

if ($all -contains $false) {
    Write-Host ""
    Write-Host "Smoke check FAILED."
    exit 1
}

Write-Host ""
Write-Host "Smoke check PASSED."
