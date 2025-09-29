#!/usr/bin/env fish

# Fish Function Test Framework
# Provides utilities for testing fish functions in isolation

# Test result tracking
set -g FISH_TEST_TOTAL 0
set -g FISH_TEST_PASSED 0
set -g FISH_TEST_FAILED 0
set -g FISH_TEST_CURRENT ""

# Test setup and teardown
function test_setup --description "Setup test environment"
    # Create temporary directories for testing
    set -g TEST_TEMP_DIR (mktemp -d)
    set -g TEST_HOME_DIR "$TEST_TEMP_DIR/home"
    set -g TEST_CONFIG_DIR "$TEST_HOME_DIR/.config"

    mkdir -p "$TEST_CONFIG_DIR/gita"
    mkdir -p "$TEST_CONFIG_DIR/fish/functions"

    # Override HOME for tests
    set -gx HOME "$TEST_HOME_DIR"
    set -gx XDG_CONFIG_HOME "$TEST_CONFIG_DIR"
end

function test_teardown --description "Clean up test environment"
    if test -n "$TEST_TEMP_DIR" -a -d "$TEST_TEMP_DIR"
        rm -rf "$TEST_TEMP_DIR"
    end

    # Restore original HOME
    set -e HOME
    set -e XDG_CONFIG_HOME
    set -e TEST_TEMP_DIR
    set -e TEST_HOME_DIR
    set -e TEST_CONFIG_DIR
end

# Test assertion functions
function assert_equals --description "Assert two values are equal"
    set -l expected "$argv[1]"
    set -l actual "$argv[2]"
    set -l message "$argv[3]"

    if test "$expected" = "$actual"
        test_pass "$message"
    else
        test_fail "$message" "Expected: '$expected', Got: '$actual'"
    end
end

function assert_contains --description "Assert string contains substring"
    set -l haystack "$argv[1]"
    set -l needle "$argv[2]"
    set -l message "$argv[3]"

    if string match -q "*$needle*" "$haystack"
        test_pass "$message"
    else
        test_fail "$message" "String '$haystack' does not contain '$needle'"
    end
end

function assert_not_contains --description "Assert string does not contain substring"
    set -l haystack "$argv[1]"
    set -l needle "$argv[2]"
    set -l message "$argv[3]"

    if not string match -q "*$needle*" "$haystack"
        test_pass "$message"
    else
        test_fail "$message" "String '$haystack' unexpectedly contains '$needle'"
    end
end

function assert_true --description "Assert condition is true (exit code 0)"
    set -l message "$argv[1]"

    if test $status -eq 0
        test_pass "$message"
    else
        test_fail "$message" "Expected true (exit code 0), got exit code $status"
    end
end

function assert_false --description "Assert condition is false (non-zero exit code)"
    set -l message "$argv[1]"

    if test $status -ne 0
        test_pass "$message"
    else
        test_fail "$message" "Expected false (non-zero exit code), got exit code 0"
    end
end

function assert_file_exists --description "Assert file exists"
    set -l file "$argv[1]"
    set -l message "$argv[2]"

    if test -f "$file"
        test_pass "$message"
    else
        test_fail "$message" "File '$file' does not exist"
    end
end

function assert_command_exists --description "Assert command is available"
    set -l cmd "$argv[1]"
    set -l message "$argv[2]"

    if command -q "$cmd"
        test_pass "$message"
    else
        test_fail "$message" "Command '$cmd' is not available"
    end
end

# Mock system functions
function mock_command --description "Mock a system command"
    set -l cmd_name "$argv[1]"
    set -l mock_script "$argv[2]"

    # Create mock script in PATH
    set -l mock_dir "$TEST_TEMP_DIR/bin"
    mkdir -p "$mock_dir"

    echo "#!/bin/bash" > "$mock_dir/$cmd_name"
    echo "$mock_script" >> "$mock_dir/$cmd_name"
    chmod +x "$mock_dir/$cmd_name"

    # Add to PATH
    set -gx PATH "$mock_dir" $PATH
end

function create_test_file --description "Create a test file with content"
    set -l file_path "$argv[1]"
    set -l content "$argv[2]"

    mkdir -p (dirname "$file_path")
    echo "$content" > "$file_path"
end

# Test execution functions
function run_test --description "Run a test function"
    set -l test_name "$argv[1]"
    set -g FISH_TEST_CURRENT "$test_name"

    echo "🧪 Running test: $test_name"

    # Setup test environment
    test_setup

    # Run the test function
    if functions -q "$test_name"
        eval "$test_name"
    else
        test_fail "Test function '$test_name' not found" ""
    end

    # Cleanup test environment
    test_teardown

    echo ""
end

function test_pass --description "Mark test as passed"
    set -l message "$argv[1]"
    set -g FISH_TEST_TOTAL (math $FISH_TEST_TOTAL + 1)
    set -g FISH_TEST_PASSED (math $FISH_TEST_PASSED + 1)
    echo "  ✅ $message"
end

function test_fail --description "Mark test as failed"
    set -l message "$argv[1]"
    set -l details "$argv[2]"
    set -g FISH_TEST_TOTAL (math $FISH_TEST_TOTAL + 1)
    set -g FISH_TEST_FAILED (math $FISH_TEST_FAILED + 1)
    echo "  ❌ $message"
    if test -n "$details"
        echo "     $details"
    end
end

function test_summary --description "Show test results summary"
    echo "📊 Test Results Summary:"
    echo "   Total:  $FISH_TEST_TOTAL"
    echo "   Passed: $FISH_TEST_PASSED"
    echo "   Failed: $FISH_TEST_FAILED"

    if test $FISH_TEST_FAILED -eq 0
        echo "🎉 All tests passed!"
        return 0
    else
        echo "💥 Some tests failed!"
        return 1
    end
end

# Source all function files for testing
function load_functions --description "Load fish functions for testing"
    set -l functions_dir "$argv[1]"

    if test -d "$functions_dir"
        for function_file in "$functions_dir"/*.fish
            if test -f "$function_file"
                source "$function_file"
            end
        end
    end
end