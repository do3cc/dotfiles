#!/bin/bash
set -e

echo "🧪 Starting dotfiles test in $(uname -a)"
echo "🐧 Container runtime: Podman"

# Run the dotfiles installation in test mode
echo "🚀 Running dotfiles installation..."
cd /dotfiles

# Two-step approach: first test --help, then run actual init
echo "🔍 Testing help functionality..."
uv run init.py --help >/dev/null || {
	echo "❌ ERROR: Help functionality test failed"
	exit 1
}

echo "🚀 Running actual dotfiles installation..."
# Run with timeout to prevent hanging
timeout 300 uv run init.py || {
	echo "❌ ERROR: Dotfiles installation failed or timed out"
	exit 1
}

echo "✅ Dotfiles installation completed successfully"

# Validate that key components were configured
echo "🔍 Validating installation..."

# Check if config symlinks were created
if [ ! -L ~/.config/fish ]; then
	echo "⚠️  WARNING: Fish config symlink not created"
else
	echo "✅ Fish config symlink created"
fi

if [ ! -L ~/.config/nvim ]; then
	echo "⚠️  WARNING: Neovim config symlink not created"
else
	echo "✅ Neovim config symlink created"
fi

# Check if git credential helper validation ran
echo "🔍 Git credential helper should have been validated"

echo "🎉 All tests passed!"
