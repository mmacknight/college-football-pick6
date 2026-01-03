#!/bin/bash

# Build Lambda layer dependencies with Docker for Linux compatibility

set -e

echo "🐳 Building Lambda layer with Docker..."

# Clean and prepare
rm -rf python/
mkdir -p python/shared

# Run pip install in a Linux container with x86_64 platform targeting
docker run --rm --platform linux/amd64 \
    -v "$(pwd)":/workspace \
    -w /workspace \
    python:3.11-slim \
    bash -c "pip install --target python/ -r requirements.txt"

# Copy shared modules
cp ../../lambdas/shared/*.py python/shared/
cp ../../lambdas/shared/python/responses.py python/shared/
touch python/shared/__init__.py

echo "✅ Lambda layer built successfully with Linux-compatible dependencies!"
echo "📂 Contents:"
ls -la python/
echo "📂 Shared modules:"
ls -la python/shared/
