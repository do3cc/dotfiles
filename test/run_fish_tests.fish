#!/usr/bin/env fish

# Master test runner for all fish function tests

set SCRIPT_DIR (dirname (status --current-filename))

# Source the test framework
source "$SCRIPT_DIR/fish_test_framework.fish"

# Initialize test counters
set -g FISH_TEST_TOTAL 0
set -g FISH_TEST_PASSED 0
set -g FISH_TEST_FAILED 0

function run_all_fish_tests
    echo "🧪 Running comprehensive fish function tests..."
    echo "================================================"
    echo ""

    # Load all functions for testing
    load_functions "$SCRIPT_DIR/../fish/functions"

    # Run all test suites
    echo "📋 Test Suite 1: gita-repo-discovery"
    source "$SCRIPT_DIR/test_gita_repo_discovery.fish"
    run_all_gita_repo_discovery_tests
    echo ""

    echo "📋 Test Suite 2: gita-worktree-detect"
    source "$SCRIPT_DIR/test_gita_worktree_detect.fish"
    run_all_gita_worktree_detect_tests
    echo ""

    echo "📋 Test Suite 3: gita-batch-fetch"
    source "$SCRIPT_DIR/test_gita_batch_fetch.fish"
    run_all_gita_batch_fetch_tests
    echo ""

    echo "📋 Test Suite 4: gita-worktree-check"
    source "$SCRIPT_DIR/test_gita_worktree_check.fish"
    run_all_gita_worktree_check_tests
    echo ""

    echo "📋 Test Suite 5: gita interactive functions"
    source "$SCRIPT_DIR/test_gita_interactive_functions.fish"
    run_all_gita_interactive_tests
    echo ""

    # Final summary
    echo "================================================"
    echo "🏁 Final Test Results Summary:"
    echo "   Total Tests:  $FISH_TEST_TOTAL"
    echo "   Passed:       $FISH_TEST_PASSED"
    echo "   Failed:       $FISH_TEST_FAILED"
    echo "   Success Rate: "(math "round($FISH_TEST_PASSED * 100 / $FISH_TEST_TOTAL)")"%"

    if test $FISH_TEST_FAILED -eq 0
        echo "🎉 All fish function tests passed!"
        return 0
    else
        echo "💥 Some fish function tests failed!"
        return 1
    end
end

# Run tests if script is executed directly
if test (status --current-filename) = (status --filename)
    run_all_fish_tests
end