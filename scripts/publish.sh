#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# CorvusTunnel Production Image Publisher
# Builds, verifies, and pushes the production Docker image.
#
# Usage:
#   ./scripts/publish.sh              # builds and pushes :latest
#   ./scripts/publish.sh 1.0.0        # builds and pushes :1.0.0
# ──────────────────────────────────────────────────────────────────────
set -e

REGISTRY="${CORVUS_REGISTRY:-corvustunnel/corvustunnel}"
VERSION="${1:-latest}"
IMAGE="${REGISTRY}:${VERSION}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "════════════════════════════════════════════════════════"
echo "  CorvusTunnel Production Build"
echo "  Image: ${IMAGE}"
echo "════════════════════════════════════════════════════════"
echo ""

# Step 1: Build production image
echo "▸ Building production image..."
docker build -f Dockerfile.prod -t "$IMAGE" .
echo ""

# Step 2: Verify no source code leaked
echo "▸ Verifying build..."
bash "${SCRIPT_DIR}/verify_build.sh" "$IMAGE"
echo ""

# Step 3: Also tag as latest if versioned
if [ "$VERSION" != "latest" ]; then
    docker tag "$IMAGE" "${REGISTRY}:latest"
    echo "▸ Also tagged as ${REGISTRY}:latest"
fi

# Step 4: Push
echo "▸ Pushing to registry..."
docker push "$IMAGE"
if [ "$VERSION" != "latest" ]; then
    docker push "${REGISTRY}:latest"
fi

echo ""
echo "════════════════════════════════════════════════════════"
echo "  ✅ Published: ${IMAGE}"
echo "════════════════════════════════════════════════════════"
