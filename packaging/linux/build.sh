#!/bin/bash
# ============================================================================
# Audex DEB Package - Simple wrapper script to build DEB package using Docker
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Check if VERSION file exists
if [ !  -f "$PROJECT_ROOT/VERSION" ]; then
    echo "❌ VERSION file not found in project root"
    exit 1
fi

# Read version from file
VERSION=$(cat "$PROJECT_ROOT/VERSION" | tr -d '[:space:]')

# Parse architecture argument
ARCH="${1:-arm64}"

echo "🐳 Building Audex DEB package in Docker..."
echo ""
echo "  Version: $VERSION"
echo "  Architecture: $ARCH"
echo ""

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t audex-builder -f "$SCRIPT_DIR/Dockerfile-build" "$SCRIPT_DIR"

# Run the build
echo ""
echo "🔨 Running build..."
docker run --rm \
  -v "$PROJECT_ROOT/dist:/build/output" \
  -v "$PROJECT_ROOT/VERSION:/build/VERSION:ro" \
  -v "$PROJECT_ROOT/audex/view/static/images/logo.svg:/build/logo.svg:ro" \
  audex-builder \
  "$VERSION" "$ARCH"

echo ""
echo "✅ Build complete!  DEB package is in: dist/"
echo ""
echo "📋 Next steps:"
echo "  1. Test the package:"
echo "     cd $SCRIPT_DIR"
echo "     ./test.sh $ARCH"
echo ""
