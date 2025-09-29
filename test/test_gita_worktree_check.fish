#!/usr/bin/env fish

# Tests for gita-worktree-check.fish

source (dirname (status --current-filename))/fish_test_framework.fish

function test_gita_worktree_check_gita_not_available
    # Mock gita command to not exist
    mock_command "gita" "exit 127"

    # Function should return 0 when gita is not available
    gita-worktree-check
    assert_true "Function returns 0 when gita command is not available"
end

function test_gita_worktree_check_no_repositories
    # Mock gita command to exist
    mock_command "gita" "echo 'gita command available'"

    # Mock gita-repo-discovery to return no repositories
    function gita-repo-discovery
        # Return empty output
    end

    # Function should handle empty repository list gracefully
    set -l output (gita-worktree-check 2>&1)

    assert_equals "" "$output" "Function produces no output when no repositories found"
end

function test_gita_worktree_check_no_worktree_repositories
    # Mock gita command to exist
    mock_command "gita" "echo 'gita command available'"

    # Mock gita-repo-discovery to return repositories
    function gita-repo-discovery
        echo "repo1"
        echo "repo2"
    end

    # Mock gita-worktree-detect to return false for all repos
    function gita-worktree-detect
        return 1
    end

    # Function should produce no output when no repos have worktrees
    set -l output (gita-worktree-check 2>&1)

    assert_equals "" "$output" "Function produces no output when no repositories use worktrees"
end

function test_gita_worktree_check_blacklisted_repository
    # Mock gita command to exist
    mock_command "gita" "echo 'gita command available'"

    # Create blacklist file
    create_test_file "$TEST_CONFIG_DIR/gita-worktree-blacklist" "blacklisted-repo
another-blacklisted-repo"

    # Mock gita-repo-discovery to return repositories including blacklisted one
    function gita-repo-discovery
        echo "normal-repo"
        echo "blacklisted-repo"
    end

    # Mock gita-worktree-detect to return true for all repos
    function gita-worktree-detect
        return 0
    end

    # Mock functions for issue detection
    function gita-worktree-detect-issues
        echo "Sample issue for $argv[1]"
    end

    # Function should skip blacklisted repositories
    set -l output (gita-worktree-check 2>&1)

    assert_contains "$output" "normal-repo" "Function processes non-blacklisted repository"
    assert_not_contains "$output" "blacklisted-repo" "Function skips blacklisted repository"
end

function test_gita_worktree_check_no_issues_found
    # Mock gita command to exist
    mock_command "gita" "echo 'gita command available'"

    # Mock gita-repo-discovery to return repositories
    function gita-repo-discovery
        echo "clean-repo1"
        echo "clean-repo2"
    end

    # Mock gita-worktree-detect to return true
    function gita-worktree-detect
        return 0
    end

    # Mock gita-worktree-detect-issues to return no issues
    function gita-worktree-detect-issues
        # Return empty output - no issues
    end

    # Function should produce no output when no issues found
    set -l output (gita-worktree-check 2>&1)

    assert_equals "" "$output" "Function produces no output when no issues found"
end

function test_gita_worktree_check_issues_found_single_repo
    # Mock gita command to exist
    mock_command "gita" "echo 'gita command available'"

    # Mock gita-repo-discovery to return one repository
    function gita-repo-discovery
        echo "problem-repo"
    end

    # Mock gita-worktree-detect to return true
    function gita-worktree-detect
        return 0
    end

    # Mock gita-worktree-detect-issues to return issues
    function gita-worktree-detect-issues
        echo "Merged branch: feature-123 can be cleaned up"
        echo "Stale worktree: /path/to/old-worktree"
    end

    # Function should report issues with proper formatting
    set -l output (gita-worktree-check 2>&1)

    assert_contains "$output" "🔧 Worktree maintenance suggestions:" "Function shows header when issues found"
    assert_contains "$output" "Repository: problem-repo" "Function shows repository name"
    assert_contains "$output" "Merged branch: feature-123" "Function shows first issue"
    assert_contains "$output" "Stale worktree: /path/to/old-worktree" "Function shows second issue"
end

function test_gita_worktree_check_issues_found_multiple_repos
    # Mock gita command to exist
    mock_command "gita" "echo 'gita command available'"

    # Mock gita-repo-discovery to return multiple repositories
    function gita-repo-discovery
        echo "repo1"
        echo "repo2"
        echo "repo3"
    end

    # Mock gita-worktree-detect to return true
    function gita-worktree-detect
        return 0
    end

    # Mock gita-worktree-detect-issues to return different issues per repo
    function gita-worktree-detect-issues
        switch $argv[1]
            case "repo1"
                echo "Issue in repo1"
            case "repo2"
                # No issues for repo2
            case "repo3"
                echo "Issue A in repo3"
                echo "Issue B in repo3"
        end
    end

    # Function should report issues for multiple repositories
    set -l output (gita-worktree-check 2>&1)

    assert_contains "$output" "🔧 Worktree maintenance suggestions:" "Function shows header when issues found"
    assert_contains "$output" "Repository: repo1" "Function shows repo1"
    assert_contains "$output" "Issue in repo1" "Function shows repo1 issue"
    assert_not_contains "$output" "Repository: repo2" "Function skips repo2 with no issues"
    assert_contains "$output" "Repository: repo3" "Function shows repo3"
    assert_contains "$output" "Issue A in repo3" "Function shows repo3 issue A"
    assert_contains "$output" "Issue B in repo3" "Function shows repo3 issue B"
end

function test_gita_worktree_check_background_fetch
    # Mock gita command to exist
    mock_command "gita" "echo 'gita command available'"

    # Mock gita-repo-discovery to return repositories
    function gita-repo-discovery
        echo "fetch-repo1"
        echo "fetch-repo2"
    end

    # Mock gita-worktree-detect to return true
    function gita-worktree-detect
        return 0
    end

    # Mock gita-worktree-detect-issues to return no issues
    function gita-worktree-detect-issues
        # Return empty output
    end

    # Mock gita-batch-fetch to track calls
    function gita-batch-fetch
        echo "Background fetch called" > "$TEST_TEMP_DIR/fetch_called"
    end

    # Function should call background fetch
    gita-worktree-check >/dev/null 2>&1

    assert_file_exists "$TEST_TEMP_DIR/fetch_called" "Function calls background fetch"
end

function test_gita_worktree_check_blacklist_file_missing
    # Mock gita command to exist
    mock_command "gita" "echo 'gita command available'"

    # Mock gita-repo-discovery to return repositories
    function gita-repo-discovery
        echo "normal-repo"
    end

    # Mock gita-worktree-detect to return true
    function gita-worktree-detect
        return 0
    end

    # Mock gita-worktree-detect-issues to return no issues
    function gita-worktree-detect-issues
        # Return empty output
    end

    # No blacklist file exists - function should handle gracefully
    set -l output (gita-worktree-check 2>&1)

    # Should not crash and should process the repository
    assert_equals "" "$output" "Function handles missing blacklist file gracefully"
end

function test_gita_worktree_check_empty_blacklist_file
    # Mock gita command to exist
    mock_command "gita" "echo 'gita command available'"

    # Create empty blacklist file
    create_test_file "$TEST_CONFIG_DIR/gita-worktree-blacklist" ""

    # Mock gita-repo-discovery to return repositories
    function gita-repo-discovery
        echo "normal-repo"
    end

    # Mock gita-worktree-detect to return true
    function gita-worktree-detect
        return 0
    end

    # Mock gita-worktree-detect-issues to return no issues
    function gita-worktree-detect-issues
        # Return empty output
    end

    # Function should handle empty blacklist file
    set -l output (gita-worktree-check 2>&1)

    assert_equals "" "$output" "Function handles empty blacklist file gracefully"
end

function test_gita_worktree_check_performance_many_repos
    # Mock gita command to exist
    mock_command "gita" "echo 'gita command available'"

    # Mock gita-repo-discovery to return many repositories
    function gita-repo-discovery
        for i in (seq 1 50)
            echo "repo$i"
        end
    end

    # Mock gita-worktree-detect to return false for all (fast path)
    function gita-worktree-detect
        return 1
    end

    # Measure execution time
    set -l start_time (date +%s%N)
    gita-worktree-check >/dev/null 2>&1
    set -l end_time (date +%s%N)
    set -l duration (math "($end_time - $start_time) / 1000000")  # Convert to milliseconds

    # Should complete quickly even with many repositories
    if test $duration -lt 1000  # Less than 1 second
        test_pass "Function completes quickly with many repositories (${duration}ms)"
    else
        test_fail "Function is too slow with many repositories" "Took ${duration}ms, expected < 1000ms"
    end
end

# Test runner
function run_all_gita_worktree_check_tests
    echo "🧪 Running gita-worktree-check tests..."

    # Load the function under test
    load_functions (dirname (status --current-filename))/../fish/functions

    run_test test_gita_worktree_check_gita_not_available
    run_test test_gita_worktree_check_no_repositories
    run_test test_gita_worktree_check_no_worktree_repositories
    run_test test_gita_worktree_check_blacklisted_repository
    run_test test_gita_worktree_check_no_issues_found
    run_test test_gita_worktree_check_issues_found_single_repo
    run_test test_gita_worktree_check_issues_found_multiple_repos
    run_test test_gita_worktree_check_background_fetch
    run_test test_gita_worktree_check_blacklist_file_missing
    run_test test_gita_worktree_check_empty_blacklist_file
    run_test test_gita_worktree_check_performance_many_repos

    test_summary
end

# Run tests if script is executed directly
if test (status --current-filename) = (status --filename)
    run_all_gita_worktree_check_tests
end