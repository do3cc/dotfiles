.PHONY: test test-arch test-debian test-ubuntu clean help

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
	@podman run --rm \
		-e DOTFILES_ENVIRONMENT=private \
		-v $(PWD):/dotfiles:Z \
		-w /dotfiles \
		dotfiles-test-arch \
		bash -c "uv run init.py --test"
	@echo "✅ Arch Linux test completed"

# Test on Debian
test-debian:
	@echo "🧪 Testing dotfiles installation on Debian..."
	@podman build -f test/Dockerfile.debian -t dotfiles-test-debian .
	@podman run --rm \
		-e DOTFILES_ENVIRONMENT=private \
		-v $(PWD):/dotfiles:Z \
		-w /dotfiles \
		dotfiles-test-debian \
		bash -c "uv run init.py --test"
	@echo "✅ Debian test completed"

# Test on Ubuntu (Debian-based)
test-ubuntu:
	@echo "🧪 Testing dotfiles installation on Ubuntu..."
	@podman build -f test/Dockerfile.ubuntu -t dotfiles-test-ubuntu .
	@podman run --rm \
		-e DOTFILES_ENVIRONMENT=private \
		-v $(PWD):/dotfiles:Z \
		-w /dotfiles \
		dotfiles-test-ubuntu \
		bash -c "uv run init.py --test"
	@echo "✅ Ubuntu test completed"

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

# Test a specific OS (usage: make test-os OS=arch)
test-os:
	@if [ -z "$(OS)" ]; then \
		echo "❌ ERROR: Please specify OS (arch, debian, ubuntu)"; \
		echo "Usage: make test-os OS=arch"; \
		exit 1; \
	fi
	@make test-$(OS)