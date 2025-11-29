#!/bin/sh
# ============================================================================
# Development Tools Script
# ============================================================================
# Description: Unified entry point for development code generation tools
# Usage: dev.sh <command> [options]
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

Development code generation tools

Commands:
  filters <gen|clean>    Generate or clean entity filter builders
  stubs <gen|clean>      Generate or clean entity stubs
  all <gen|clean>        Run all generators

Options:
  --force                Overwrite/remove without confirmation
  -q, --quiet            Suppress non-error output
  -h, --help             Show this help message

Examples:
  $(basename "$0") filters gen
  $(basename "$0") filters gen --force
  $(basename "$0") stubs clean
  $(basename "$0") all gen --quiet

EOF
}

run_genfilters() {
	command="$1"
	shift

	log_step "Running filter generator..."
	python3 "$SCRIPT_DIR/genfilters.py" "$command" "$@"
}

run_genstubs() {
	command="$1"
	shift

	log_step "Running stub generator..."
	python3 "$SCRIPT_DIR/genstubs.py" "$command" "$@"
}

run_all() {
	command="$1"
	shift

	print_header "Running All Generators"

	run_genfilters "$command" "$@"
	echo ""
	run_genstubs "$command" "$@"

	echo ""
	log_success "All generators completed"
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
		filters)
			shift
			if [ $# -eq 0 ]; then
				log_error "Command required: gen or clean"
				exit 1
			fi
			run_genfilters "$@"
			;;
		stubs)
			shift
			if [ $# -eq 0 ]; then
				log_error "Command required: gen or clean"
				exit 1
			fi
			run_genstubs "$@"
			;;
		all)
			shift
			if [ $# -eq 0 ]; then
				log_error "Command required: gen or clean"
				exit 1
			fi
			run_all "$@"
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
