.PHONY: clean dev pre-commit

VENV_NAME := .venv
PYTHON := $(VENV_NAME)/bin/python
PORT ?= 8000

# Run the FastAPI application in development mode
dev:
	@echo "Starting FastAPI application in development mode..."
	@$(PYTHON) -m uvicorn main:app --reload --port $(PORT)

# Clean up python cache files
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -type f -name "*.pyd" -delete
	@find . -type d -name ".ruff_cache" -exec rm -rf {} +
	@echo "Clean up complete!"

# Run pre-commit hooks
pre-commit:
	@echo "Running pre-commit hooks..."
	@$(VENV_NAME)/bin/pre-commit run --all-files
	@echo "Pre-commit hooks complete!"
