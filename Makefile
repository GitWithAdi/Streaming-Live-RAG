.PHONY: help test bench stream1 stream2 stream3 ablations docker-build docker-run

help:
	@echo "Streaming Live RAG Engine - Command Shortcuts"
	@echo "  make test        : Run full pytest suite (15 tests)"
	@echo "  make bench       : Run automated G1-G6 acceptance gate benchmark"
	@echo "  make stream1     : Simulate Example 1 (Incremental Multi-Intent Stream)"
	@echo "  make stream2     : Simulate Example 2 (Late-Arriving Constraint Refinement)"
	@echo "  make stream3     : Simulate Example 3 (Presentation Query Suppression)"
	@echo "  make ablations   : Run architectural ablation experiments"
	@echo "  make docker-run  : Build and run containerized benchmark suite"

test:
	python -m pytest tests/ -v

bench:
	python -m evaluation.benchmark_runner

stream1:
	python cli.py --stream-example 1

stream2:
	python cli.py --stream-example 2

stream3:
	python cli.py --stream-example 3

ablations:
	python cli.py --ablations

docker-build:
	docker compose build

docker-run:
	docker compose up --build
