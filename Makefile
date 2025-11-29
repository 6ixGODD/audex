# ============================================================================
# Makefile for Audex Project
# ============================================================================
# Description: Unified command interface for development, build, and deployment
# ============================================================================

.PHONY: help
.DEFAULT_GOAL := help

# ============================================================================
# Variables
# ============================================================================

PYTHON := python3
POETRY := poetry
MKDOCS := mkdocs
SCRIPTS_DIR := scripts
PACKAGING_DIR := packaging/linux

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

# ============================================================================
# Help
# ============================================================================

help: ## Show this help message
	@echo "$(BLUE)Audex Project Makefile$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Examples:$(NC)"
	@echo "  make install          # Install dependencies"
	@echo "  make dev-gen          # Generate all code"
	@echo "  make build            # Build Python package"
	@echo "  make test             # Run tests"
	@echo "  make bump VERSION=1.0.4  # Bump version"
	@echo ""

# ============================================================================
# Development Setup
# ============================================================================

install: ## Install project dependencies with Poetry
	@echo "$(BLUE)Installing dependencies... $(NC)"
	$(POETRY) install
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(POETRY) install --with dev
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

install-docs: ## Install documentation dependencies
	@echo "$(BLUE)Installing documentation dependencies...$(NC)"
	$(POETRY) install --with docs
	@echo "$(GREEN)✓ Documentation dependencies installed$(NC)"

install-all: ## Install all dependencies (including dev and docs)
	@echo "$(BLUE)Installing all dependencies...$(NC)"
	$(POETRY) install --with dev,docs
	@echo "$(GREEN)✓ All dependencies installed$(NC)"

setup: install-all ## Complete development setup
	@echo "$(GREEN)✓ Development environment ready$(NC)"

# ============================================================================
# Code Generation
# ============================================================================

dev-gen: ## Generate all code (filters + stubs)
	@echo "$(BLUE)Generating code...$(NC)"
	@sh $(SCRIPTS_DIR)/dev.sh all gen
	@echo "$(GREEN)✓ Code generation complete$(NC)"

dev-gen-filters: ## Generate entity filters
	@sh $(SCRIPTS_DIR)/dev.sh filters gen

dev-gen-stubs: ## Generate entity stubs
	@sh $(SCRIPTS_DIR)/dev.sh stubs gen

dev-clean: ## Clean all generated code
	@sh $(SCRIPTS_DIR)/dev.sh all clean --force

dev-clean-filters: ## Clean generated filters
	@sh $(SCRIPTS_DIR)/dev.sh filters clean --force

dev-clean-stubs: ## Clean generated stubs
	@sh $(SCRIPTS_DIR)/dev.sh stubs clean --force

# ============================================================================
# Code Quality
# ============================================================================

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	$(POETRY) run black audex/
	$(POETRY) run isort audex/
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Run linters (ruff, mypy)
	@echo "$(BLUE)Running linters...$(NC)"
	$(POETRY) run ruff check audex/
	$(POETRY) run mypy audex/
	@echo "$(GREEN)✓ Linting complete$(NC)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Type checking...$(NC)"
	$(POETRY) run mypy audex/
	@echo "$(GREEN)✓ Type checking complete$(NC)"

check: format lint ## Run all code quality checks

# ============================================================================
# Testing
# ============================================================================

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(POETRY) run pytest
	@echo "$(GREEN)✓ Tests passed$(NC)"

test-cov: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(POETRY) run pytest --cov=audex --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated: htmlcov/index.html$(NC)"

test-watch: ## Run tests in watch mode
	$(POETRY) run pytest-watch

# ============================================================================
# Build
# ============================================================================

build: ## Build Python package (wheel + sdist)
	@echo "$(BLUE)Building Python package...$(NC)"
	@sh $(SCRIPTS_DIR)/build.sh python
	@echo "$(GREEN)✓ Package built$(NC)"

build-clean: ## Clean and rebuild Python package
	@echo "$(BLUE)Cleaning and building...$(NC)"
	@sh $(SCRIPTS_DIR)/build.sh python --clean
	@echo "$(GREEN)✓ Clean build complete$(NC)"

build-docs: ## Build documentation with MkDocs
	@echo "$(BLUE)Building documentation...$(NC)"
	@sh $(SCRIPTS_DIR)/build.sh docs
	@echo "$(GREEN)✓ Documentation built: site/$(NC)"

build-deb-arm64: ## Build DEB package for ARM64
	@echo "$(BLUE)Building DEB for ARM64...$(NC)"
	@sh $(SCRIPTS_DIR)/build.sh deb arm64
	@echo "$(GREEN)✓ DEB package built$(NC)"

build-deb-amd64: ## Build DEB package for AMD64
	@echo "$(BLUE)Building DEB for AMD64...$(NC)"
	@sh $(SCRIPTS_DIR)/build.sh deb amd64
	@echo "$(GREEN)✓ DEB package built$(NC)"

build-deb: build-deb-arm64 build-deb-amd64 ## Build DEB packages for all architectures

build-all: build build-docs ## Build everything (Python + docs)

# ============================================================================
# Version Management
# ============================================================================

bump: ## Bump version (usage: make bump VERSION=1.0.4)
ifndef VERSION
	@echo "$(YELLOW)Error: VERSION is required$(NC)"
	@echo "Usage: make bump VERSION=1.0.4"
	@exit 1
endif
	@echo "$(BLUE)Bumping version to $(VERSION)...$(NC)"
	@sh $(SCRIPTS_DIR)/bump.sh $(VERSION)
	@echo "$(GREEN)✓ Version bumped to $(VERSION)$(NC)"

bump-dry: ## Dry-run version bump (usage: make bump-dry VERSION=1.0.4)
ifndef VERSION
	@echo "$(YELLOW)Error: VERSION is required$(NC)"
	@echo "Usage: make bump-dry VERSION=1.0.4"
	@exit 1
endif
	@sh $(SCRIPTS_DIR)/bump.sh $(VERSION) --dry-run

bump-no-push: ## Bump version without pushing to remote
ifndef VERSION
	@echo "$(YELLOW)Error: VERSION is required$(NC)"
	@echo "Usage: make bump-no-push VERSION=1.0.4"
	@exit 1
endif
	@sh $(SCRIPTS_DIR)/bump.sh $(VERSION) --no-push

# ============================================================================
# Deployment
# ============================================================================

deploy-test: ## Deploy to TestPyPI
	@echo "$(BLUE)Deploying to TestPyPI...$(NC)"
	@sh $(SCRIPTS_DIR)/deploy.sh pypi test
	@echo "$(GREEN)✓ Deployed to TestPyPI$(NC)"

deploy-pypi: ## Deploy to production PyPI
	@echo "$(BLUE)Deploying to PyPI...$(NC)"
	@sh $(SCRIPTS_DIR)/deploy.sh pypi prod
	@echo "$(GREEN)✓ Deployed to PyPI$(NC)"

deploy-docs: ## Deploy documentation to GitHub Pages
	@echo "$(BLUE)Deploying documentation...$(NC)"
	@sh $(SCRIPTS_DIR)/deploy.sh docs
	@echo "$(GREEN)✓ Documentation deployed$(NC)"

test-deb-arm64: ## Test DEB package on ARM64
	@sh $(SCRIPTS_DIR)/deploy.sh deb arm64

test-deb-amd64: ## Test DEB package on AMD64
	@sh $(SCRIPTS_DIR)/deploy.sh deb amd64

# ============================================================================
# Documentation
# ============================================================================

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Starting documentation server...$(NC)"
	$(MKDOCS) serve

docs-build: build-docs ## Alias for build-docs

docs-deploy: deploy-docs ## Alias for deploy-docs

# ============================================================================
# Cleaning
# ============================================================================

clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	@rm -rf dist/ build/ *.egg-info .pytest_cache .mypy_cache .ruff_cache
	@rm -rf site/ htmlcov/ .coverage
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Cleaned$(NC)"

clean-all: clean dev-clean ## Clean everything (build + generated code)
	@echo "$(GREEN)✓ All artifacts cleaned$(NC)"

# ============================================================================
# Development Workflow
# ============================================================================

dev: install-all dev-gen ## Complete development setup with code generation
	@echo "$(GREEN)✓ Development environment ready$(NC)"

check-all: format lint test ## Run all checks (format + lint + test)
	@echo "$(GREEN)✓ All checks passed$(NC)"

pre-commit: check-all ## Run pre-commit checks
	@echo "$(GREEN)✓ Pre-commit checks passed$(NC)"

pre-release: clean-all build-all test ## Prepare for release
	@echo "$(GREEN)✓ Ready for release$(NC)"

# ============================================================================
# Release Workflow
# ============================================================================

release: ## Full release workflow (bump + build + deploy)
ifndef VERSION
	@echo "$(YELLOW)Error: VERSION is required$(NC)"
	@echo "Usage: make release VERSION=1.0.4"
	@exit 1
endif
	@echo "$(BLUE)Starting release workflow for version $(VERSION)...$(NC)"
	@$(MAKE) pre-release
	@$(MAKE) bump VERSION=$(VERSION)
	@echo "$(GREEN)✓ Release complete!  GitHub Actions will handle deployment.$(NC)"

release-manual: ## Manual release (bump + build + manual deploy)
ifndef VERSION
	@echo "$(YELLOW)Error: VERSION is required$(NC)"
	@echo "Usage: make release-manual VERSION=1.0.4"
	@exit 1
endif
	@$(MAKE) pre-release
	@$(MAKE) bump-no-push VERSION=$(VERSION)
	@$(MAKE) deploy-pypi
	@echo "$(YELLOW)Remember to push manually:$(NC)"
	@echo "  git push origin main"
	@echo "  git push origin v$(VERSION)"

# ============================================================================
# CI/CD Simulation
# ============================================================================

ci: ## Simulate CI pipeline locally
	@echo "$(BLUE)Running CI pipeline...$(NC)"
	@$(MAKE) install-all
	@$(MAKE) check-all
	@$(MAKE) build-all
	@echo "$(GREEN)✓ CI pipeline passed$(NC)"

# ============================================================================
# Utilities
# ============================================================================

shell: ## Open Poetry shell
	$(POETRY) shell

info: ## Show project information
	@echo "$(BLUE)Project Information:$(NC)"
	@echo ""
	@echo "Python version:"
	@$(PYTHON) --version
	@echo ""
	@echo "Poetry version:"
	@$(POETRY) --version
	@echo ""
	@echo "Project dependencies:"
	@$(POETRY) show --tree

update: ## Update dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	$(POETRY) update
	@echo "$(GREEN)✓ Dependencies updated$(NC)"

lock: ## Update lock file
	@echo "$(BLUE)Updating lock file...$(NC)"
	$(POETRY) lock
	@echo "$(GREEN)✓ Lock file updated$(NC)"

# ============================================================================
# Docker (if needed in future)
# ============================================================================

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t audex:latest .
	@echo "$(GREEN)✓ Docker image built$(NC)"

docker-run: ## Run Docker container
	docker run --rm -it audex:latest

# ============================================================================
# Quick Commands (Aliases)
# ============================================================================

b: build ## Alias for build
t: test ## Alias for test
c: check ## Alias for check
f: format ## Alias for format
l: lint ## Alias for lint
i: install ## Alias for install
