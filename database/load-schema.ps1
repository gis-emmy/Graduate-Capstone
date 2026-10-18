#!/usr/bin/env powershell
# TDOT Database Schema Loader

$dbHost = "localhost"
$dbPort = "5432"
$dbName = "tdot_env"
$dbUser = "postgres"
$dbPassword = "dev-password"
$schemaFile = "database\schema.sql"

Write-Host "TDOT Database Schema Loader`n" -ForegroundColor Cyan

# Check PostgreSQL client
$psqlPath = "C:\Program Files\PostgreSQL\15\bin\psql.exe"
if (-not (Test-Path $psqlPath)) {
    $psqlPath = (Get-Command psql -ErrorAction SilentlyContinue).Source
    if (-not $psqlPath) {
        Write-Host "ERROR: PostgreSQL client not found in PATH" -ForegroundColor Red
        exit 1
    }
}

# Check schema file
if (-not (Test-Path $schemaFile)) {
    Write-Host "ERROR: Schema file not found at $schemaFile" -ForegroundColor Red
    exit 1
}

# Test connection
$env:PGPASSWORD = $dbPassword
& $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -c "SELECT 1;" 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Could not connect to database" -ForegroundColor Red
    Write-Host "postgresql://$dbUser@$dbHost`:$dbPort/$dbName" -ForegroundColor Yellow
    exit 1
}

# Load schema
Write-Host "Loading schema..." -ForegroundColor Yellow
$output = & $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -f $schemaFile 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Schema loaded successfully!" -ForegroundColor Green
    
    # Verify tables
    $query = "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
    $tables = & $psqlPath -h $dbHost -p $dbPort -U $dbUser -d $dbName -t -c $query 2>&1
    
    Write-Host "`nTables created:" -ForegroundColor Green
    $tables | ForEach-Object { if ($_) { Write-Host "  • $_" -ForegroundColor White } }
} else {
    Write-Host "ERROR: Schema loading failed" -ForegroundColor Red
    Write-Host $output -ForegroundColor Yellow
    exit 1
}

$env:PGPASSWORD = $null
Write-Host "`nDatabase setup complete!`n" -ForegroundColor Green
