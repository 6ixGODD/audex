#!/bin/bash
# Interactive test script for Audex DEB package

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Find the latest DEB file
DEB_FILE=$(ls -t "$PROJECT_ROOT/dist"/audex_*.deb 2>/dev/null | head -1)

if [ -z "$DEB_FILE" ]; then
    echo "❌ No DEB package found in dist/"
    echo "   Run ./build.sh first"
    exit 1
fi

DEB_NAME=$(basename "$DEB_FILE")

echo "🐳 Starting interactive test environment..."
echo ""
echo "  Package: $DEB_NAME"
echo ""

# Build test image
echo "📦 Building test Docker image..."
docker build \
  -t audex-test \
  -f "$SCRIPT_DIR/Dockerfile-test" \
  --build-arg DEB_FILE="$DEB_FILE" \
  --build-arg GUIDE_SCRIPT="$SCRIPT_DIR/guide.sh" \
  "$PROJECT_ROOT"

echo ""
echo "🚀 Launching interactive container..."
echo ""

# Run interactive container
docker run -it --rm audex-test
