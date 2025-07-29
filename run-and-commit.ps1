# Infinite loop
while ($true) {
    Write-Host "Running main.py at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

    # Activate your virtual environment if you use one
    # & "path\to\venv\Scripts\Activate.ps1"

    # Run the Python script
    python .\main.py

    # Git commands to commit and push changes
    git add .\docs\
    $datetime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    git commit -m "update at $datetime" 2>$null
    git push

    Write-Host "Changes pushed. Sleeping for 3 hours..."
    
    # Wait 3 hours (10,800 seconds)
    Start-Sleep -Seconds 10800
}
