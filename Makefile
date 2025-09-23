.PHONY: test test-arch test-debian test-ubuntu clean help cache-start cache-stop cache-stats cache-images

# Default target
help:
	@echo "Available targets:"
	@echo "  test        - Run tests on all supported OS containers"
	@echo "  test-arch   - Test on Arch Linux container"
	@echo "  test-debian - Test on Debian container"
	@echo "  test-ubuntu - Test on Ubuntu container"
	@echo "  cache-start - Start HTTP caching proxy"
	@echo "  cache-stop  - Stop HTTP caching proxy"
	@echo "  cache-stats - Show HTTP cache statistics"
	@echo "  cache-images- Pre-pull base images for faster builds"
	@echo "  clean       - Remove test containers and images"
	@echo "  help        - Show this help message"

# Run all tests
test: test-arch test-debian test-ubuntu
	@echo "✅ All tests completed"

# Test on Arch Linux
test-arch:
	@echo "🧪 Testing dotfiles installation on Arch Linux..."
	@if [ -d ~/.cache/dotfiles-build ]; then \
		echo "📦 Using build cache..."; \
		podman build -f test/Dockerfile.arch -t dotfiles-test-arch \
			-v ~/.cache/dotfiles-build:/cache:Z \
			-v ~/.cache/dotfiles-build/pacman:/var/cache/pacman/pkg:Z .; \
	else \
		podman build -f test/Dockerfile.arch -t dotfiles-test-arch .; \
	fi
	@echo "🚀 Running Arch test with improved logging..."
	@podman run --rm \
		-e DOTFILES_ENVIRONMENT=private \
		-e PYTHONUNBUFFERED=1 \
		-v $(PWD):/dotfiles:Z \
		-v ~/.cache/dotfiles-build/uv-cache:/cache/uv-cache:Z \
		-w /dotfiles \
		dotfiles-test-arch \
		bash -c "set -x && \
			sudo rm -rf .venv && \
			echo '📦 Installing project dependencies...' && \
			UV_LINK_MODE=copy uv sync && \
			echo '🚀 Starting dotfiles installation...' && \
			export DOTFILES_ENVIRONMENT=private && \
			timeout 300 uv run dotfiles-init --test || echo '⚠️ Test timed out after 5 minutes'"
	@echo "✅ Arch Linux test completed"

# Test on Debian
test-debian:
	@echo "🧪 Testing dotfiles installation on Debian..."
	@if [ -d ~/.cache/dotfiles-build ]; then \
		echo "📦 Using build cache..."; \
		podman build -f test/Dockerfile.debian -t dotfiles-test-debian \
			-v ~/.cache/dotfiles-build:/cache:Z \
			-v ~/.cache/dotfiles-build/apt:/var/cache/apt/archives:Z .; \
	else \
		podman build -f test/Dockerfile.debian -t dotfiles-test-debian .; \
	fi
	@echo "🚀 Running Debian test with improved logging..."
	@podman run --rm \
		-e DOTFILES_ENVIRONMENT=private \
		-e PYTHONUNBUFFERED=1 \
		-v $(PWD):/dotfiles:Z \
		-v ~/.cache/dotfiles-build/uv-cache:/cache/uv-cache:Z \
		-w /dotfiles \
		dotfiles-test-debian \
		bash -c "set -x && \
			sudo rm -rf .venv && \
			echo '📦 Installing project dependencies...' && \
			UV_LINK_MODE=copy uv sync && \
			echo '🚀 Starting dotfiles installation...' && \
			export DOTFILES_ENVIRONMENT=private && \
			timeout 300 uv run dotfiles-init --test || echo '⚠️ Test timed out after 5 minutes'"
	@echo "✅ Debian test completed"

# Test on Ubuntu (Debian-based)
test-ubuntu:
	@echo "🧪 Testing dotfiles installation on Ubuntu..."
	@if [ -d ~/.cache/dotfiles-build ]; then \
		echo "📦 Using build cache..."; \
		podman build -f test/Dockerfile.ubuntu -t dotfiles-test-ubuntu \
			-v ~/.cache/dotfiles-build:/cache:Z \
			-v ~/.cache/dotfiles-build/apt:/var/cache/apt/archives:Z .; \
	else \
		podman build -f test/Dockerfile.ubuntu -t dotfiles-test-ubuntu .; \
	fi
	@echo "🚀 Running Ubuntu test with improved logging..."
	podman run --rm \
		-e DOTFILES_ENVIRONMENT=private \
		-e PYTHONUNBUFFERED=1 \
		-v $(PWD):/dotfiles:O \
		-v ~/.cache/dotfiles-build/uv-cache:/cache/uv-cache:Z \
		-v ~/.cache/dotfiles-build/uv-python-cache:/home/testuser/.local/share/uv/python:Z \
		-w /dotfiles \
		dotfiles-test-ubuntu \
		bash -c "set -x && \
			sudo chown -R testuser:testuser . && \
			sudo rm -rf .venv && \
			echo '📦 Installing project dependencies...' && \
			UV_LINK_MODE=copy uv sync && \
			echo '🚀 Starting dotfiles installation...' && \
			export DOTFILES_ENVIRONMENT=private && \
			timeout 300 uv run dotfiles-init --test || echo '⚠️ Test timed out after 5 minutes'"
	@echo "✅ Ubuntu test completed"

# Start caching by creating cache directory and pre-downloading
cache-start:
	@echo "🚀 Setting up build cache..."
	@echo "📦 Setting up cache directories..."
	@mkdir -p ~/.cache/dotfiles-build/{pacman,apt,uv,uv-cache,uv-python-cache}
	@chmod 777 ~/.cache/dotfiles-build/{uv-python-cache,uv-cache}
	@echo "📥 Pre-pulling base images..."
	@podman pull archlinux:latest &
	@podman pull debian:bookworm &
	@podman pull ubuntu:22.04 &
	@wait
	@echo "📦 Caching uv installer..."
	@curl -LsSf https://astral.sh/uv/install.sh -o ~/.cache/dotfiles-build/uv/install.sh
	@chmod +x ~/.cache/dotfiles-build/uv/install.sh
	@echo "✅ Build cache ready at ~/.cache/dotfiles-build/"

# Clear build cache
cache-stop:
	@echo "🧹 Clearing build cache..."
	@rm -rf ~/.cache/dotfiles-build
	@podman rmi archlinux:latest debian:bookworm ubuntu:22.04 2>/dev/null || true
	@echo "✅ Build cache cleared"

# Show cache statistics
cache-stats:
	@echo "📊 Build Cache Statistics:"
	@if [ -d ~/.cache/dotfiles-build ]; then \
		echo "Cache Status: 🟢 Active"; \
		echo "Cache Location: ~/.cache/dotfiles-build"; \
		echo "Cache Size: $$(du -sh ~/.cache/dotfiles-build 2>/dev/null | cut -f1)"; \
		echo ""; \
		echo "📁 Cached Files:"; \
		ls -lah ~/.cache/dotfiles-build/ 2>/dev/null || echo "No cached files"; \
		echo ""; \
		echo "🖼️  Cached Images:"; \
		podman images --format "{{.Repository}}:{{.Tag}} {{.Size}}" | grep -E "(archlinux|debian|ubuntu)" || echo "No cached images"; \
	else \
		echo "Cache Status: 🔴 Not active"; \
		echo "Run 'make cache-start' to set up build cache"; \
	fi

# Pre-pull base images for faster builds
cache-images:
	@echo "📥 Pre-pulling base images..."
	@podman pull archlinux:latest
	@podman pull debian:bookworm
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
