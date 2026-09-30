# One-command CLI runner for Windows PowerShell
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Starting Streaming Live RAG Engine (Gate G1 Evaluation)  " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

python -m evaluation.benchmark_runner
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nAll benchmark gates passed successfully!" -ForegroundColor Green
} else {
    Write-Host "`nBenchmark failed. Please inspect logs above." -ForegroundColor Red
}
