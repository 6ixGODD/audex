#!/bin/bash
# Interactive test script for Audex DEB package

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Parse architecture argument
if [ -z "$1" ]; then
    echo "Usage: $0 <architecture>"
    echo ""
    echo "Available packages:"
    ls -1 "$PROJECT_ROOT/dist"/audex_*.deb 2>/dev/null || echo "  (none found)"
    echo ""
    echo "Example:"
    echo "  $0 amd64    # Test amd64 package"
    echo "  $0 arm64    # Test arm64 package"
    exit 1
fi

DEB_ARCH="$1"

# Find the DEB file matching specified architecture
DEB_FILE=$(ls -t "$PROJECT_ROOT/dist"/audex_*_${DEB_ARCH}.deb 2>/dev/null | head -1)

if [ -z "$DEB_FILE" ]; then
    echo "❌ No $DEB_ARCH DEB package found in dist/"
    echo "   Available packages:"
    ls -1 "$PROJECT_ROOT/dist"/audex_*.deb 2>/dev/null || echo "  (none)"
    echo ""
    echo "   Build one with: ./build.sh $DEB_ARCH"
    exit 1
fi

DEB_NAME=$(basename "$DEB_FILE")

echo "🐳 Starting interactive test environment..."
echo ""
echo "  Package: $DEB_NAME"
echo "  Architecture: $DEB_ARCH"
echo ""

# Build test image for the specified architecture
echo "📦 Building test Docker image..."
docker build \
  -t audex-test-${DEB_ARCH} \
  -f "$SCRIPT_DIR/Dockerfile-test" \
  --build-arg DEB_FILE="dist/$DEB_NAME" \
  --build-arg GUIDE_SCRIPT="packaging/linux/guide.sh" \
  --platform linux/${DEB_ARCH} \
  "$PROJECT_ROOT"

echo ""
echo "🚀 Launching interactive container..."
echo ""

# Run interactive container with matching platform
docker run -it --rm \
  --platform linux/${DEB_ARCH} \
  audex-test-${DEB_ARCH}
