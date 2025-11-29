#!/bin/sh
# ============================================================================
# Deploy & Test Script
# ============================================================================
# Description: Deploy and test Audex packages
# Usage: deploy.sh <command> [options]
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=scripts/tools/common.sh
.  "$SCRIPT_DIR/tools/common.sh"

# ============================================================================
# Functions
# ============================================================================

show_usage() {
	cat <<EOF
Usage: $(basename "$0") <command> [options]

Deploy and test tools

Commands:
  pypi <test|prod>       Deploy to PyPI (TestPyPI or production)
  deb <arch>             Test DEB package installation
  docs                   Deploy documentation (GitHub Pages)

Options:
  -h, --help             Show this help message

Examples:
  $(basename "$0") pypi test
  $(basename "$0") pypi prod
  $(basename "$0") deb arm64
  $(basename "$0") docs

EOF
}

deploy_pypi() {
	target="$1"

	if [ "$target" != "test" ] && [ "$target" != "prod" ]; then
		log_error "Target must be 'test' or 'prod'"
		exit 1
	fi

	log_step "Deploying to $([ "$target" = "test" ] && echo "TestPyPI" || echo "PyPI")..."

	cd "$PROJECT_ROOT"

	if !  command_exists poetry; then
		die "Poetry is not installed"
	fi

	# Build if no dist/
	if [ ! -d "dist" ] || [ -z "$(ls -A dist 2>/dev/null)" ]; then
		log_info "No build artifacts found, building..."
		poetry build
	fi

	# Configure repository
	if [ "$target" = "test" ]; then
		poetry config repositories.testpypi https://test.pypi.org/legacy/
		poetry publish -r testpypi
	else
		if !  confirm "Deploy to production PyPI?"; then
			log_info "Deployment cancelled"
			exit 0
		fi
		poetry publish
	fi

	log_success "Deployment complete"
}

test_deb() {
	arch="$1"

	if [ -z "$arch" ]; then
		log_error "Architecture required: arm64 or amd64"
		exit 1
	fi

	log_step "Testing DEB package for $arch..."

	cd "$PROJECT_ROOT/packaging/linux"

	if [ !  -f "test.sh" ]; then
		die "test.sh not found in packaging/linux/"
	fi

	chmod +x test.sh
	./test.sh "$arch"
}

deploy_docs() {
	log_step "Deploying documentation..."

	cd "$PROJECT_ROOT"

	if !  command_exists mkdocs; then
		die "MkDocs is not installed"
	fi

	if !  confirm "Deploy documentation to GitHub Pages?"; then
		log_info "Deployment cancelled"
		exit 0
	fi

	mkdocs gh-deploy

	log_success "Documentation deployed"
}

# ============================================================================
# Main
# ============================================================================

main() {
	if [ $# -eq 0 ]; then
		show_usage
		exit 1
	fi

	case "$1" in
		pypi)
			shift
			if [ $# -eq 0 ]; then
				log_error "Target required: test or prod"
				exit 1
			fi
			deploy_pypi "$@"
			;;
		deb)
			shift
			test_deb "$@"
			;;
		docs)
			deploy_docs
			;;
		-h|--help)
			show_usage
			exit 0
			;;
		*)
			log_error "Unknown command: $1"
			show_usage
			exit 1
			;;
	esac
}

main "$@"
