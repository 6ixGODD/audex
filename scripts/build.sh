#!/bin/sh
# ============================================================================
# Build Script
# ============================================================================
# Description: Unified build tool for Python packages, documentation, and DEB
# Usage: build.sh <command> [options]
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=scripts/tools/common.sh
. "$SCRIPT_DIR/tools/common.sh"

# ============================================================================
# Functions
# ============================================================================

show_usage() {
	cat <<EOF
Usage: $(basename "$0") <command> [options]

Build tools for Audex project

Commands:
  python                 Build Python wheel/sdist with Poetry
  docs                   Build documentation with MkDocs
  deb <arch>             Build DEB package (arm64/amd64)
  all                    Build everything (Python + docs)

Options:
  --clean                Clean build artifacts before building
  -h, --help             Show this help message

Examples:
  $(basename "$0") python
  $(basename "$0") python --clean
  $(basename "$0") docs
  $(basename "$0") deb arm64
  $(basename "$0") all

EOF
}

build_python() {
	clean="$1"

	log_step "Building Python package..."

	cd "$PROJECT_ROOT"

	if [ "$clean" = "clean" ]; then
		log_info "Cleaning previous builds..."
		rm -rf dist/ build/ *.egg-info
	fi

	if !  command_exists poetry; then
		die "Poetry is not installed. Install: pip install poetry"
	fi

	poetry build

	echo ""
	log_success "Python package built successfully"
	log_info "Artifacts in: dist/"
	ls -lh dist/
}

build_docs() {
	clean="$1"

	log_step "Building documentation..."

	cd "$PROJECT_ROOT"

	if [ "$clean" = "clean" ]; then
		log_info "Cleaning previous docs..."
		rm -rf site/
	fi

	if ! command_exists mkdocs; then
		die "MkDocs is not installed. Install: pip install mkdocs mkdocs-material"
	fi

	mkdocs build

	echo ""
	log_success "Documentation built successfully"
	log_info "Artifacts in: site/"
}

build_deb() {
	arch="$1"

	if [ -z "$arch" ]; then
		log_error "Architecture required: arm64 or amd64"
		exit 1
	fi

	log_step "Building DEB package for $arch..."

	cd "$PROJECT_ROOT/packaging/linux"

	if [ !  -f "$PROJECT_ROOT/VERSION" ]; then
		die "VERSION file not found in project root"
	fi

	chmod +x build.sh
	./build.sh "$arch"

	echo ""
	log_success "DEB package built successfully"
	log_info "Artifacts in: dist/"
	ls -lh "$PROJECT_ROOT/dist"/*.deb
}

build_all() {
	clean="$1"

	print_header "Building All Artifacts"

	build_python "$clean"
	echo ""
	build_docs "$clean"

	echo ""
	log_success "All builds completed"
}

# ============================================================================
# Main
# ============================================================================

main() {
	if [ $# -eq 0 ]; then
		show_usage
		exit 1
	fi

	CLEAN_FLAG=""

	case "$1" in
		python)
			shift
			if [ "$1" = "--clean" ]; then
				CLEAN_FLAG="clean"
			fi
			build_python "$CLEAN_FLAG"
			;;
		docs)
			shift
			if [ "$1" = "--clean" ]; then
				CLEAN_FLAG="clean"
			fi
			build_docs "$CLEAN_FLAG"
			;;
		deb)
			shift
			build_deb "$@"
			;;
		all)
			shift
			if [ "$1" = "--clean" ]; then
				CLEAN_FLAG="clean"
			fi
			build_all "$CLEAN_FLAG"
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
