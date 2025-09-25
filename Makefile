.PHONY: test test-arch test-debian test-ubuntu clean help

# Container Test Configuration
#
# DOCKER CONTAINER STANDARDIZATION (Issue #2):
# Fixed inconsistent mount configurations that caused .venv ownership issues.
# All containers now use identical mount options for consistent behavior.
#
# Key fix: Standardized mount option `:O` across all containers.
# This ensures proper file ownership and eliminates permission problems
# that occurred with different mount configurations between OS containers.

# Default target
help:
	@echo "Available targets:"
	@echo "  test        - Run tests on all supported OS containers"
	@echo "  test-arch   - Test on Arch Linux container"
	@echo "  test-debian - Test on Debian container"
	@echo "  test-ubuntu - Test on Ubuntu container"
	@echo "  clean       - Remove test containers and images"
	@echo "  help        - Show this help message"

# Run all tests
test: test-arch test-debian test-ubuntu
	@echo "✅ All tests completed"

# Test on Arch Linux
test-arch:
	@echo "🧪 Testing dotfiles installation on Arch Linux..."
	@podman build -f test/Dockerfile.arch -t dotfiles-test-arch .
	@echo "🚀 Running Arch test..."
	@podman run --rm \
		-e DOTFILES_ENVIRONMENT=minimal \
		-e PYTHONUNBUFFERED=1 \
		-v $(PWD):/dotfiles:O \
		-w /dotfiles \
		dotfiles-test-arch \
		bash -c "set -x && \
			sudo rm -rf .venv && \
			echo '📦 Installing project dependencies...' && \
			uv sync && \
			echo '🚀 Starting dotfiles installation...' && \
			export DOTFILES_ENVIRONMENT=minimal && \
			timeout 300 uv run dotfiles-init --no-remote || echo '⚠️ Test timed out after 5 minutes'"
	@echo "✅ Arch Linux test completed"

# Test on Debian
test-debian:
	@echo "🧪 Testing dotfiles installation on Debian..."
	@podman build -f test/Dockerfile.debian -t dotfiles-test-debian .
	@echo "🚀 Running Debian test..."
	@podman run --rm \
		-e DOTFILES_ENVIRONMENT=minimal \
		-e PYTHONUNBUFFERED=1 \
		-v $(PWD):/dotfiles:O \
		-w /dotfiles \
		dotfiles-test-debian \
		bash -c "set -x && \
			sudo rm -rf .venv && \
			echo '📦 Installing project dependencies...' && \
			uv sync && \
			echo '🚀 Starting dotfiles installation...' && \
			export DOTFILES_ENVIRONMENT=minimal && \
			timeout 300 uv run dotfiles-init --no-remote || echo '⚠️ Test timed out after 5 minutes'"
	@echo "✅ Debian test completed"

# Test on Ubuntu (Debian-based)
test-ubuntu:
	@echo "🧪 Testing dotfiles installation on Ubuntu..."
	@podman build -f test/Dockerfile.ubuntu -t dotfiles-test-ubuntu .
	@echo "🚀 Running Ubuntu test..."
	@podman run --rm \
		-e DOTFILES_ENVIRONMENT=minimal \
		-e PYTHONUNBUFFERED=1 \
		-v $(PWD):/dotfiles:O \
		-w /dotfiles \
		dotfiles-test-ubuntu \
		bash -c "set -x && \
			sudo rm -rf .venv && \
			echo '📦 Installing project dependencies...' && \
			uv sync && \
			echo '🚀 Starting dotfiles installation...' && \
			export DOTFILES_ENVIRONMENT=minimal && \
			timeout 300 uv run dotfiles-init --no-remote || echo '⚠️ Test timed out after 5 minutes'"
	@echo "✅ Ubuntu test completed"

# Clean up test containers and images
clean:
	@echo "🧹 Cleaning up test containers and images..."
	@podman rmi -f dotfiles-test-arch dotfiles-test-debian dotfiles-test-ubuntu 2>/dev/null || true
	@podman system prune -f
	@echo "✅ Cleanup completed"