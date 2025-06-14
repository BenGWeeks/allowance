#!/bin/bash
# Test script to reproduce CI environment and capture LNBits startup errors

echo "🔍 Testing LNBits startup in CI-like environment..."

# Check if we're in a git repo
if [ ! -d ".git" ]; then
    echo "❌ Not in git repository root"
    exit 1
fi

# Create a temporary directory for testing
TEMP_DIR=$(mktemp -d)
echo "📁 Using temp directory: $TEMP_DIR"

# Clone LNBits (simulate CI environment)
echo "📥 Cloning LNBits..."
cd "$TEMP_DIR"
git clone https://github.com/lnbits/lnbits.git
cd lnbits

# Copy the extension files
echo "📋 Copying allowance extension..."
EXTENSION_DIR="lnbits/extensions/allowance"
mkdir -p "$EXTENSION_DIR"

# Go back to original directory to copy files
ORIGINAL_DIR=$(cd - > /dev/null && pwd)
cp -r "$ORIGINAL_DIR"/*.py "$EXTENSION_DIR/" 2>/dev/null || true
cp -r "$ORIGINAL_DIR"/*.json "$EXTENSION_DIR/" 2>/dev/null || true
cp -r "$ORIGINAL_DIR"/static "$EXTENSION_DIR/" 2>/dev/null || true
cp -r "$ORIGINAL_DIR"/templates "$EXTENSION_DIR/" 2>/dev/null || true

# Setup environment
echo "🔧 Setting up environment..."
cp .env.example .env
cat >> .env << EOF
LNBITS_BACKEND_WALLET_CLASS=VoidWallet
LNBITS_DATABASE_URL=postgres://postgres:postgres@localhost:5432/lnbits
LNBITS_EXTENSIONS_DEFAULT_INSTALL=allowance
HOST=0.0.0.0
PORT=5000
DEBUG=true
LNBITS_FORCE_HTTPS=false
EOF

# Export environment variables
export LNBITS_BACKEND_WALLET_CLASS=VoidWallet
export LNBITS_DATABASE_URL=postgres://postgres:postgres@localhost:5432/lnbits
export LNBITS_EXTENSIONS_DEFAULT_INSTALL=allowance
export HOST=0.0.0.0
export PORT=5000
export DEBUG=true
export LNBITS_FORCE_HTTPS=false

# Check Python and Poetry
echo "🐍 Python version:"
python3 --version

echo "📦 Checking Poetry..."
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry not found. Installing..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

poetry --version

# Install dependencies
echo "📦 Installing dependencies..."
poetry install --without dev || {
    echo "❌ Failed to install dependencies"
    exit 1
}

# Test import
echo "🧪 Testing Python import..."
poetry run python -c "import lnbits; print('✅ LNBits import successful')" 2>&1 || {
    echo "❌ LNBits import failed with error:"
    poetry run python -c "import lnbits" 2>&1
}

# Test help command
echo "🧪 Testing LNBits --help..."
poetry run python -m lnbits --help 2>&1 | head -10 || {
    echo "❌ LNBits --help failed"
}

# Try to start LNBits with full error capture
echo "🚀 Attempting to start LNBits..."
timeout 10 poetry run python -u -m lnbits 2>&1 | tee lnbits-startup.log || {
    EXIT_CODE=$?
    echo "❌ LNBits failed with exit code: $EXIT_CODE"
    echo "📋 Full error log:"
    cat lnbits-startup.log
}

# Cleanup
echo "🧹 Cleaning up..."
cd "$ORIGINAL_DIR"
rm -rf "$TEMP_DIR"

echo "✅ Test complete"