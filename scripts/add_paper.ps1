param([string]$PdfPath)

if (-not $PdfPath) {
    Write-Error "Provide path to PDF"
    exit 1
}

$env:ONEDRIVE_PAPERS_ROOT = Split-Path $PdfPath -Parent
python "$PSScriptRoot/paper_sync.py"
