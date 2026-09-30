#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  Starting Streaming Live RAG Engine (Gate G1 Evaluation)  "
echo "============================================================"

python -m evaluation.benchmark_runner
echo ""
echo "All benchmark gates passed successfully!"
