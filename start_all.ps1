# Start RTL-Gen AI - All Services
Write-Host "Starting RTL-Gen AI..." -ForegroundColor Cyan

# Start PostgreSQL
docker start rtlgenai-postgres 2>$null
Write-Host "PostgreSQL: started" -ForegroundColor Green

# Start API server
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command", "cd 'C:\Users\venka\Documents\rtl-gen-aii'; python api.py" `
    -WindowStyle Normal

Write-Host "API server: http://localhost:8502" -ForegroundColor Green
Write-Host "API docs:   http://localhost:8502/docs" -ForegroundColor Green
Start-Sleep 3

# Start Streamlit
Write-Host "Streamlit UI: http://localhost:8501" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop Streamlit (API will continue)" -ForegroundColor Yellow
Write-Host ""

Set-Location "C:\Users\venka\Documents\rtl-gen-aii"
streamlit run app.py
