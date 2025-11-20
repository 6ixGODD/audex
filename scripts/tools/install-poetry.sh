#!/bin/sh
# ============================================================================
# Install Poetry
# ============================================================================
# Description: Install Poetry using the official installer
# Usage: scripts/tools/install-poetry.sh
# ============================================================================

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source common utilities
# shellcheck source=bin/tools/common.sh
. "$SCRIPT_DIR/common.sh"

# Check if Poetry is already installed
check_existing() {
	if command_exists poetry; then
		log_warn "Poetry is already installed"
		poetry --version
		echo ""
		if confirm "Do you want to reinstall?"; then
			return 0
		else
			log_info "Installation cancelled"
			exit 0
		fi
	fi
}

# Install Poetry using official installer
install_poetry() {
	log_step "Downloading Poetry installer..."

	if command_exists curl; then
		curl -sSL https://install.python-poetry.org | python3 -
	elif command_exists wget; then
		wget -qO- https://install.python-poetry.org | python3 -
	else
		die "Neither curl nor wget is available. Please install curl or wget first"
	fi
}

# Configure Poetry
configure_poetry() {
	log_step "Configuring Poetry..."

	# Add Poetry to PATH for current session
	export PATH="$HOME/.local/bin:$PATH"

	# Configure Poetry to create virtual environments in project directory
	if command_exists poetry; then
		poetry config virtualenvs.in-project true
		log_success "Poetry configured successfully"
	else
		log_warn "Poetry command not found in current session"
	fi
}

# Display post-installation instructions
show_instructions() {
	print_header "Poetry Installation Complete!"

	echo "Please add Poetry to your PATH by adding this line to your shell config:"
	echo ""
	echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
	echo ""
	echo "Shell config files:"
	echo "  - bash: ~/.bashrc or ~/.bash_profile"
	echo "  - zsh: ~/.zshrc"
	echo "  - fish: ~/.config/fish/config.fish"
	echo ""
	echo "After updating your shell config, restart your terminal or run:"
	echo "  source ~/.bashrc  # or your shell config file"
	echo ""
	log_info "Verify installation with: poetry --version"
	echo ""
}

main() {
	print_header "Poetry Installation"

	check_existing
	install_poetry
	configure_poetry
	show_instructions

	log_success "Installation script complete"
}

main
