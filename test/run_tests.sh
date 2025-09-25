#!/bin/bash

# Dotfiles Testing Script using Podman
# This script tests the init.py installation on different Linux distributions

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🧪 Starting dotfiles testing with Podman containers"
echo "📁 Project directory: $PROJECT_DIR"

# Function to run a test
run_test() {
	local distro=$1
	local environment=${2:-minimal}
	local containerfile="$SCRIPT_DIR/Containerfile.$distro"
	local image_name="dotfiles-test-$distro"
	local container_name="dotfiles-test-$distro-$(date +%s)"

	echo "🐧 Testing $distro with $environment environment..."

	# Build the container image
	echo "🔨 Building container image for $distro..."
	if ! podman build -t "$image_name" -f "$containerfile" "$PROJECT_DIR"; then
		echo "❌ Failed to build $distro container"
		return 1
	fi

	# Run the test
	echo "🚀 Running test for $distro..."
	if podman run --rm --name "$container_name" "$image_name" sh -c "DOTFILES_ENVIRONMENT=$environment uv run dotfiles-init --no-remote"; then
		echo "✅ $distro test passed!"
		return 0
	else
		echo "❌ $distro test failed!"
		return 1
	fi
}

# Function to cleanup images
cleanup() {
	echo "🧹 Cleaning up test images..."
	podman rmi -f dotfiles-test-arch 2>/dev/null || true
	podman rmi -f dotfiles-test-debian 2>/dev/null || true
	echo "✨ Cleanup complete"
}

# Parse command line arguments
DISTROS=()
ENVIRONMENT="minimal"
CLEANUP_AFTER=false

while [[ $# -gt 0 ]]; do
	case $1 in
	--arch)
		DISTROS+=("arch")
		shift
		;;
	--debian)
		DISTROS+=("debian")
		shift
		;;
	--all)
		DISTROS=("arch" "debian")
		shift
		;;
	--environment)
		ENVIRONMENT="$2"
		shift 2
		;;
	--cleanup)
		CLEANUP_AFTER=true
		shift
		;;
	--help)
		echo "Usage: $0 [OPTIONS]"
		echo ""
		echo "Options:"
		echo "  --arch                 Test Arch Linux only"
		echo "  --debian               Test Debian only"
		echo "  --all                  Test all distributions (default)"
		echo "  --environment ENV      Test environment (minimal|work|private, default: minimal)"
		echo "  --cleanup              Cleanup images after testing"
		echo "  --help                 Show this help message"
		echo ""
		echo "Examples:"
		echo "  $0 --all                           # Test all distributions with minimal environment"
		echo "  $0 --arch --environment private    # Test Arch with private environment"
		echo "  $0 --debian --cleanup              # Test Debian and cleanup afterward"
		exit 0
		;;
	*)
		echo "Unknown option: $1"
		echo "Use --help for usage information"
		exit 1
		;;
	esac
done

# Default to all distributions if none specified
if [[ ${#DISTROS[@]} -eq 0 ]]; then
	DISTROS=("arch" "debian")
fi

# Check if podman is available
if ! command -v podman &>/dev/null; then
	echo "❌ Podman is not installed. Please install podman to run tests."
	exit 1
fi

# Run tests
FAILED_TESTS=()
PASSED_TESTS=()

for distro in "${DISTROS[@]}"; do
	if run_test "$distro" "$ENVIRONMENT"; then
		PASSED_TESTS+=("$distro")
	else
		FAILED_TESTS+=("$distro")
	fi
	echo ""
done

# Cleanup if requested
if [[ "$CLEANUP_AFTER" == "true" ]]; then
	cleanup
fi

# Summary
echo "📊 Test Results Summary:"
echo "✅ Passed: ${#PASSED_TESTS[@]} (${PASSED_TESTS[*]})"
echo "❌ Failed: ${#FAILED_TESTS[@]} (${FAILED_TESTS[*]})"

if [[ ${#FAILED_TESTS[@]} -eq 0 ]]; then
	echo "🎉 All tests passed!"
	exit 0
else
	echo "💥 Some tests failed!"
	exit 1
fi
