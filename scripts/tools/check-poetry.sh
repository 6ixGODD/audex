#!/bin/sh
# ============================================================================
# Check Poetry Installation
# ============================================================================
# Description: Verify if Poetry is installed and accessible
# Usage: scripts/tools/check-poetry.sh
# Exit Code: 0 if Poetry is installed, 1 otherwise
# ============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source common utilities
# shellcheck source=bin/tools/common.sh
. "$SCRIPT_DIR/common.sh"

check_poetry() {
	if command_exists poetry; then
		log_success "Poetry is installed"
		poetry --version
		return 0
	else
		log_error "Poetry is not installed"
		echo ""
		echo "Please install Poetry by running:"
		echo "  make install-poetry"
		echo ""
		echo "Or manually install from: https://python-poetry.org/docs/#installation"
		return 1
	fi
}

main() {
	check_poetry
}

main
