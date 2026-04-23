# ============================================================
# Makefile – News Alpha Engine
# ============================================================

.PHONY: help install seed test lint pipeline server dashboard docker-up docker-down clean

help:
	@echo ""
	@echo "  📈 News Alpha Engine – Command Reference"
	@echo ""
	@echo "  make install      Install Python dependencies"
	@echo "  make seed         Seed PostgreSQL with knowledge graph data"
	@echo "  make test         Run full test suite (34 tests)"
	@echo "  make lint         Run ruff linter"
	@echo "  make pipeline     Run the full daily pipeline once"
	@echo "  make server       Start FastAPI server (port 8000)"
	@echo "  make dashboard    Launch Streamlit dashboard (port 8501)"
	@echo "  make scheduler    Start automated cron scheduler"
	@echo "  make graph        Demo knowledge graph in terminal"
	@echo "  make docker-up    Start all Docker services"
	@echo "  make docker-down  Stop all Docker services"
	@echo "  make clean        Remove __pycache__, .pytest_cache, logs"
	@echo ""

install:
	pip install -r requirements.txt

seed:
	python scripts/seed_db.py

test:
	pytest tests/ -v --tb=short

test-fast:
	pytest tests/test_pipeline.py::TestKnowledgeGraph \
	       tests/test_pipeline.py::TestEventDetection \
	       tests/test_pipeline.py::TestIngestion \
	       tests/test_pipeline.py::TestLLMEngine -v

lint:
	ruff check . --fix

pipeline:
	python main.py pipeline

pipeline-dry:
	python main.py pipeline --max-articles 20

server:
	python main.py server --port 8000

dashboard:
	python main.py dashboard

scheduler:
	python main.py scheduler

graph:
	python main.py graph

docker-up:
	docker-compose up -d
	@echo "Waiting for DB to be ready..."
	@sleep 5
	docker exec newsalpha_api python scripts/seed_db.py

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f --tail=100

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf logs/*.log 2>/dev/null || true
	@echo "Cleaned."

migrate:
	alembic upgrade head

migrate-new:
	alembic revision --autogenerate -m "$(msg)"
