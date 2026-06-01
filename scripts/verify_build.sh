#!/bin/bash
# ──────────────────────────────────────────────────────────────────────
# CorvusTunnel Build Verification
# Ensures no Python source files leaked into the final Docker image.
# Run during CI/build only — never visible to customers.
# ──────────────────────────────────────────────────────────────────────
set -e

IMAGE="${1:?Usage: verify_build.sh IMAGE_NAME}"

echo "Scanning $IMAGE for Python source files..."

# Find .py files in /app (excluding pyarmor runtime which is expected)
PY_FILES=$(docker run --rm --entrypoint="" "$IMAGE" \
    find /app -name "*.py" \
    -not -path "*/pyarmor_runtime*" \
    -not -path "*/__pycache__/*" \
    2>/dev/null || true)

if [ -n "$PY_FILES" ]; then
    echo "❌ BUILD VERIFICATION FAILED"
    echo "   Python source files found in final image:"
    echo "$PY_FILES" | head -20
    echo ""
    echo "   These files should have been obfuscated by PyArmor."
    echo "   Check Dockerfile.prod stage 1."
    exit 1
fi

echo "✅ BUILD VERIFIED: No Python source files in image."

# Also check that obfuscated files DO exist
OBF_COUNT=$(docker run --rm --entrypoint="" "$IMAGE" \
    find /app -name "*.pyc" -o -name "*.so" | wc -l)

if [ "$OBF_COUNT" -eq 0 ]; then
    echo "⚠ WARNING: No obfuscated files (.pyc/.so) found either."
    echo "   PyArmor may not have run correctly."
    exit 1
fi

echo "✅ Found $OBF_COUNT obfuscated files."
