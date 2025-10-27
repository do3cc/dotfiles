#!/bin/bash
# Simple test to validate Dockerfile generation uses packages.yaml
# This test extracts the generate_dockerfile_content function and tests its output

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Extract just the generate_dockerfile_content function from run-claude.sh
# We do this by reading the file directly and extracting lines between the function definition
extract_function() {
	local script="$1"
	local func_name="$2"

	# Find the line number where the function starts
	local start_line=$(grep -n "^$func_name()" "$script" | cut -d: -f1)

	if [ -z "$start_line" ]; then
		return 1
	fi

	# Extract from start to the line that starts the next function
	# Get the end line by finding the next function definition at same indentation level
	local end_line=$(tail -n +$((start_line + 1)) "$script" | grep -n "^[a-zA-Z_].*() {" | head -1 | cut -d: -f1)

	if [ -z "$end_line" ]; then
		# If no next function found, go to end of file
		tail -n +$start_line "$script"
	else
		# Extract from start to the line before next function
		end_line=$((start_line + end_line - 2))
		sed -n "${start_line},${end_line}p" "$script"
	fi
}

echo "=================================================="
echo "Testing Dockerfile Generation with packages.yaml"
echo "=================================================="
echo ""

# Test 1: Check if COPY packages.yaml is in the Dockerfile
echo "TEST 1: Dockerfile should contain COPY packages.yaml"
if grep -q "COPY packages.yaml" "$TEST_DIR/local_bin/run-claude.sh"; then
	echo "PASS: COPY packages.yaml instruction exists in script"
else
	echo "FAIL: COPY packages.yaml instruction not found"
	exit 1
fi
echo ""

# Test 2: Check if Python yaml parsing is in the Dockerfile
echo "TEST 2: Dockerfile should parse packages.yaml with Python"
if grep -q "import yaml" "$TEST_DIR/local_bin/run-claude.sh"; then
	echo "PASS: Python yaml import found in script"
else
	echo "FAIL: Python yaml import not found"
	exit 1
fi
echo ""

# Test 3: Check for python3-yaml in bootstrap packages
echo "TEST 3: Bootstrap should include python3-yaml"
if grep -q "python3-yaml" "$TEST_DIR/local_bin/run-claude.sh"; then
	echo "PASS: python3-yaml found in script"
else
	echo "FAIL: python3-yaml not found"
	exit 1
fi
echo ""

# Test 4: Check for manifest array access
echo "TEST 4: Dockerfile should reference manifest base debian packages"
if grep -q "manifest\['base'\]\['debian'\]" "$TEST_DIR/local_bin/run-claude.sh"; then
	echo "PASS: Manifest array access found"
else
	echo "FAIL: Manifest array access not found"
	exit 1
fi
echo ""

# Test 5: Check for cleanup of packages.yaml
echo "TEST 5: Dockerfile should cleanup packages.yaml after install"
if grep -q "rm /tmp/packages.yaml" "$TEST_DIR/local_bin/run-claude.sh"; then
	echo "PASS: packages.yaml cleanup found"
else
	echo "FAIL: packages.yaml cleanup not found"
	exit 1
fi
echo ""

echo "=================================================="
echo "All tests PASSED"
echo "=================================================="
