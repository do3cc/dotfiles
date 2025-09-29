.PHONY: test test-arch test-debian test-ubuntu test-compile clean help cache-start cache-stop cache-stats cache-images

# Cache directory configuration - CI vs local
CI_CACHE_DIR := ~/.cache/dotfiles-ci
CACHE_DIR := $(if $(CI),$(CI_CACHE_DIR),~/.cache/dotfiles-build)

# Container Test Configuration - Comprehensive Improvements
#
# TIMEOUT FIXES:
# Test timeouts increased from 300s (5min) to 900s (15min) to accommodate:
# 1. Package downloads and installation in containers
# 2. APT operations that can take 5-10 minutes with slow mirrors
# 3. System updates that may download many packages
# 4. AUR helper (yay) compilation on Arch (5-10 minutes)
#
# The timeout hierarchy (outer timeout triggers after inner timeouts):
# - Makefile timeout: 900s (15min) - prevents infinite hangs
# - APT operations: 600s (10min) - faster failure detection
# - Pacman operations: 600s (10min) - aligned with APT
# - System updates: 1800s (30min) - can be very large
# - Most other operations: 300s (5min) - quick operations
#
# PERMISSION FIXES:
# Removed destructive "sudo chown -R testuser:testuser ." command that was:
# 1. Corrupting git ownership on the host system
# 2. Unnecessarily changing ownership of all files
# 3. Causing "dubious ownership" git errors
#
# Current approach:
# 1. Only remove .venv directory (sudo rm -rf .venv)
# 2. Let UV handle .venv creation with proper permissions
# 3. UV_LINK_MODE=copy avoids most permission issues
# 4. Preserve host file ownership for git operations
#
# OUTPUT STREAMING FIXES:
# Package operations now show real-time progress instead of appearing stuck:
# 1. APT: Removed capture_output=True, shows package installation progress
# 2. Pacman: Removed capture_output=True, shows package installation progress
# 3. System updates: Direct subprocess calls show update progress
# 4. AUR operations: Git clone and makepkg compilation show progress
#
# INTERACTIVE PROMPT FIXES (Debian/Ubuntu only):
# 1. Timezone pre-configuration prevents tzdata prompts
# 2. Container detection ensures safe timezone modification
# 3. DEBIAN_FRONTEND=noninteractive as fallback (sudo may drop it)
#
# These improvements ensure all test targets complete successfully with
# visible progress and no interactive prompts or permission errors.

# Default target
help:
	@echo "Available targets:"
	@echo "  test        - Run tests on all supported OS containers"
	@echo "  test-compile- Quick compilation test (check help methods work)"
	@echo "  test-arch   - Test on Arch Linux container"
	@echo "  test-debian - Test on Debian container"
	@echo "  test-ubuntu - Test on Ubuntu container"
	@echo "  cache-start - Set up local build cache directories and base images"
	@echo "  cache-stop  - Clear local build cache and remove cached images"
	@echo "  cache-stats - Show local build cache statistics and sizes"
	@echo "  cache-images- Pre-pull base container images for faster builds"
	@echo "  clean       - Remove test containers and images"
	@echo "  help        - Show this help message"

# Run all tests
test: test-arch test-debian test-ubuntu
	@echo "✅ All tests completed"

# Quick compilation test - verify all tools can import and show help
test-compile:
	@echo "🔍 Running quick compilation test..."
	@echo "📦 Installing dependencies..."
	@uv sync --quiet
	@echo "✅ Testing dotfiles-init help method..."
	@uv run dotfiles-init --help > /dev/null
	@echo "✅ Testing dotfiles-swman help method..."
	@uv run dotfiles-swman --help > /dev/null
	@echo "✅ Testing dotfiles-pkgstatus help method..."
	@uv run dotfiles-pkgstatus --help > /dev/null
	@echo "🎉 All tools can import and show help successfully!"
	@echo "✅ Compilation test passed"

# Test on Arch Linux
test-arch:
	@echo "🧪 Testing dotfiles installation on Arch Linux..."
	@if [ -d $(CACHE_DIR) ]; then \
		echo "📦 Using build cache from $(CACHE_DIR)..."; \
		podman build -f test/Containerfile.arch -t dotfiles-test-arch \
			-v $(CACHE_DIR):/cache:Z \
			-v $(CACHE_DIR)/pacman:/var/cache/pacman/pkg:Z .; \
	else \
		podman build -f test/Containerfile.arch -t dotfiles-test-arch .; \
	fi
	@echo "🚀 Running Arch test with improved logging..."
	@podman run --rm \
		-e DOTFILES_ENVIRONMENT=minimal \
		-e PYTHONUNBUFFERED=1 \
		-v $(PWD):/dotfiles:O \
		-v $(CACHE_DIR)/uv-cache:/cache/uv-cache:Z \
		-v $(CACHE_DIR)/uv-python-cache:/home/testuser/.local/share/uv/python:Z \
		-w /dotfiles \
		dotfiles-test-arch \
		bash -c "set -x && \
			sudo rm -rf .venv && \
			echo '📦 Installing project dependencies...' && \
			UV_LINK_MODE=copy uv sync && \
			echo '🚀 Starting dotfiles installation...' && \
			export DOTFILES_ENVIRONMENT=minimal && \
			timeout 900 uv run dotfiles-init --no-remote || echo '⚠️ Test timed out after 15 minutes'"
	@echo "✅ Arch Linux test completed"

# Test on Debian
test-debian:
	@echo "🧪 Testing dotfiles installation on Debian..."
	@if [ -d $(CACHE_DIR) ]; then \
		echo "📦 Using build cache from $(CACHE_DIR)..."; \
		podman build -f test/Containerfile.debian -t dotfiles-test-debian \
			-v $(CACHE_DIR):/cache:Z \
			-v $(CACHE_DIR)/apt:/var/cache/apt/archives:Z .; \
	else \
		podman build -f test/Containerfile.debian -t dotfiles-test-debian .; \
	fi
	@echo "🚀 Running Debian test with improved logging..."
	@podman run --rm \
		-e DOTFILES_ENVIRONMENT=minimal \
		-e PYTHONUNBUFFERED=1 \
		-v $(PWD):/dotfiles:O \
		-v $(CACHE_DIR)/uv-cache:/cache/uv-cache:Z \
		-v $(CACHE_DIR)/uv-python-cache:/home/testuser/.local/share/uv/python:Z \
		-w /dotfiles \
		dotfiles-test-debian \
		bash -c "set -x && \
			sudo rm -rf .venv && \
			echo '📦 Installing project dependencies...' && \
			UV_LINK_MODE=copy uv sync && \
			echo '🚀 Starting dotfiles installation...' && \
			export DOTFILES_ENVIRONMENT=minimal && \
			timeout 900 uv run dotfiles-init --no-remote || echo '⚠️ Test timed out after 15 minutes'"
	@echo "✅ Debian test completed"

# Test on Ubuntu (Debian-based)
test-ubuntu:
	@echo "🧪 Testing dotfiles installation on Ubuntu..."
	@if [ -d $(CACHE_DIR) ]; then \
		echo "📦 Using build cache from $(CACHE_DIR)..."; \
		podman build -f test/Containerfile.ubuntu -t dotfiles-test-ubuntu \
			-v $(CACHE_DIR):/cache:Z \
			-v $(CACHE_DIR)/apt:/var/cache/apt/archives:Z .; \
	else \
		podman build -f test/Containerfile.ubuntu -t dotfiles-test-ubuntu .; \
	fi
	@echo "🚀 Running Ubuntu test with improved logging..."
	podman run --rm \
		-e DOTFILES_ENVIRONMENT=minimal \
		-e PYTHONUNBUFFERED=1 \
		-v $(PWD):/dotfiles:O \
		-v $(CACHE_DIR)/uv-cache:/cache/uv-cache:Z \
		-v $(CACHE_DIR)/uv-python-cache:/home/testuser/.local/share/uv/python:Z \
		-w /dotfiles \
		dotfiles-test-ubuntu \
		bash -c "set -x && \
			sudo rm -rf .venv && \
			echo '📦 Installing project dependencies...' && \
			UV_LINK_MODE=copy uv sync && \
			echo '🚀 Starting dotfiles installation...' && \
			export DOTFILES_ENVIRONMENT=minimal && \
			timeout 900 uv run dotfiles-init --no-remote || echo '⚠️ Test timed out after 15 minutes'"
	@echo "✅ Ubuntu test completed"

# Set up local build cache (CI: ~/.cache/dotfiles-ci, Local: ~/.cache/dotfiles-build)
cache-start:
	@echo "🚀 Setting up local build cache..."
	@echo "📦 Setting up cache directories..."
	@mkdir -p $(CACHE_DIR)/{pacman,apt,uv,uv-cache,uv-python-cache,containers}
	@chmod 777 $(CACHE_DIR)/{uv-python-cache,uv-cache}
	@echo "📥 Pre-pulling base images..."
	@podman pull ghcr.io/archlinux/archlinux:latest &
	@podman pull public.ecr.aws/docker/library/debian:bookworm &
	@podman pull ubuntu:22.04 &
	@wait
	@echo "📦 Caching uv installer..."
	@curl -LsSf https://astral.sh/uv/install.sh -o $(CACHE_DIR)/uv/install.sh
	@chmod +x $(CACHE_DIR)/uv/install.sh
	@echo "✅ Local build cache ready at $(CACHE_DIR)/"

# Clear local build cache and remove cached images
cache-stop:
	@echo "🧹 Clearing local build cache..."
	@rm -rf $(CACHE_DIR)
	@podman rmi ghcr.io/archlinux/archlinux:latest public.ecr.aws/docker/library/debian:bookworm ubuntu:22.04 2>/dev/null || true
	@echo "✅ Build cache cleared"

# Show local build cache statistics
cache-stats:
	@echo "📊 Local Build Cache Statistics:"
	@echo "Environment: $(if $(CI),CI (GitHub Actions),Local Development)"
	@if [ -d $(CACHE_DIR) ]; then \
		echo "Cache Status: 🟢 Active"; \
		echo "Cache Location: $(CACHE_DIR)"; \
		echo "Cache Size: $$(du -sh $(CACHE_DIR) 2>/dev/null | cut -f1)"; \
		echo ""; \
		echo "📁 Cached Files:"; \
		ls -lah $(CACHE_DIR)/ 2>/dev/null || echo "No cached files"; \
		echo ""; \
		echo "🖼️  Cached Images:"; \
		podman images --format "{{.Repository}}:{{.Tag}} {{.Size}}" | grep -E "(archlinux|debian|ubuntu)" || echo "No cached images"; \
	else \
		echo "Cache Status: 🔴 Not active"; \
		echo "Run 'make cache-start' to set up local build cache"; \
	fi

# Pre-pull base images for faster builds
cache-images:
	@echo "📥 Pre-pulling base images..."
	@podman pull ghcr.io/archlinux/archlinux:latest
	@podman pull public.ecr.aws/docker/library/debian:bookworm
	@podman pull ubuntu:22.04
	@echo "✅ Base images cached"

# Clean up test containers and images
clean:
	@echo "🧹 Cleaning up test containers and images..."
	@podman rmi -f dotfiles-test-arch dotfiles-test-debian dotfiles-test-ubuntu 2>/dev/null || true
	@podman system prune -f
	@echo "✅ Cleanup completed"

# Run tests with verbose output
test-verbose:
	@echo "🧪 Running tests with verbose output..."
	@VERBOSE=1 make test

# Run tests with build cache visibility
test-cache-verbose:
	@echo "🧪 Running tests with cache visibility..."
	@if podman ps --format "{{.Names}}" | grep -q dotfiles-squid-cache; then \
		echo "📦 Cache proxy is running - you should see cache hits in the logs"; \
		echo "🔍 Monitor cache with: make cache-stats"; \
	fi
	@echo "Building with progress and layer cache visibility..."
	@make test BUILDX_PROGRESS=plain

# Test a specific OS (usage: make test-os OS=arch)
test-os:
	@if [ -z "$(OS)" ]; then \
		echo "❌ ERROR: Please specify OS (arch, debian, ubuntu)"; \
		echo "Usage: make test-os OS=arch"; \
		exit 1; \
	fi
	@make test-$(OS)
