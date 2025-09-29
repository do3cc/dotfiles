#!/usr/bin/env fish

# Tests for gita-batch-fetch.fish

source (dirname (status --current-filename))/fish_test_framework.fish

function test_gita_batch_fetch_no_repositories
    # Mock gita-repo-discovery to return no repositories
    function gita-repo-discovery
        # Return empty output
    end

    # Function should handle empty repository list gracefully
    set -l output (gita-batch-fetch 2>&1)

    # Should not produce any output and exit cleanly
    assert_equals "" "$output" "Function produces no output when no repositories found"
end

function test_gita_batch_fetch_single_repository
    # Mock gita-repo-discovery to return one repository
    function gita-repo-discovery
        echo "test-repo"
    end

    # Mock gita fetch to succeed
    mock_command "gita" "
        if test \"\$1\" = 'fetch' -a \"\$2\" = 'test-repo'
            echo 'Fetching test-repo...'
            exit 0
        else
            echo 'gita: unknown command'
            exit 1
        fi
    "

    # Function should fetch the single repository
    set -l output (gita-batch-fetch 2>&1)

    assert_contains "$output" "Fetching test-repo" "Function fetches the single repository"
end

function test_gita_batch_fetch_multiple_repositories
    # Mock gita-repo-discovery to return multiple repositories
    function gita-repo-discovery
        echo "repo1"
        echo "repo2"
        echo "repo3"
    end

    # Mock gita fetch to succeed for all repos
    mock_command "gita" "
        case \"\$2\" in
            'repo1')
                echo 'Fetching repo1...'
                exit 0
                ;;
            'repo2')
                echo 'Fetching repo2...'
                exit 0
                ;;
            'repo3')
                echo 'Fetching repo3...'
                exit 0
                ;;
            *)
                echo 'gita: unknown repository'
                exit 1
                ;;
        esac
    "

    # Function should fetch all repositories
    set -l output (gita-batch-fetch 2>&1)

    assert_contains "$output" "repo1" "Function fetches repo1"
    assert_contains "$output" "repo2" "Function fetches repo2"
    assert_contains "$output" "repo3" "Function fetches repo3"
end

function test_gita_batch_fetch_with_errors
    # Mock gita-repo-discovery to return repositories
    function gita-repo-discovery
        echo "good-repo"
        echo "bad-repo"
        echo "another-good-repo"
    end

    # Mock gita fetch with one failure
    mock_command "gita" "
        case \"\$2\" in
            'good-repo')
                echo 'Fetching good-repo...'
                exit 0
                ;;
            'bad-repo')
                echo 'Error: failed to fetch bad-repo' >&2
                exit 1
                ;;
            'another-good-repo')
                echo 'Fetching another-good-repo...'
                exit 0
                ;;
            *)
                echo 'gita: unknown repository'
                exit 1
                ;;
        esac
    "

    # Function should continue despite errors
    set -l output (gita-batch-fetch 2>&1)

    assert_contains "$output" "good-repo" "Function fetches successful repositories"
    assert_contains "$output" "another-good-repo" "Function continues after error"
    assert_contains "$output" "failed to fetch bad-repo" "Function reports fetch errors"
end

function test_gita_batch_fetch_silent_mode
    # Mock gita-repo-discovery to return repositories
    function gita-repo-discovery
        echo "silent-repo1"
        echo "silent-repo2"
    end

    # Mock gita fetch to produce output
    mock_command "gita" "
        if test \"\$1\" = 'fetch'
            echo \"Fetching \$2...\"
            echo \"From origin: * branch main -> FETCH_HEAD\"
            exit 0
        fi
    "

    # Function with --silent flag should suppress output
    set -l output (gita-batch-fetch --silent 2>&1)

    assert_equals "" "$output" "Silent mode produces no output"
end

function test_gita_batch_fetch_parallel_execution
    # Mock gita-repo-discovery to return multiple repositories
    function gita-repo-discovery
        echo "parallel-repo1"
        echo "parallel-repo2"
        echo "parallel-repo3"
    end

    # Mock gita fetch with delays to test parallelism
    mock_command "gita" "
        if test \"\$1\" = 'fetch'
            echo \"Starting fetch for \$2\"
            sleep 0.1  # Small delay to simulate network operation
            echo \"Completed fetch for \$2\"
            exit 0
        fi
    "

    # Measure execution time (should be faster than sequential)
    set -l start_time (date +%s%N)
    set -l output (gita-batch-fetch 2>&1)
    set -l end_time (date +%s%N)
    set -l duration (math "($end_time - $start_time) / 1000000")  # Convert to milliseconds

    assert_contains "$output" "parallel-repo1" "Function fetches repo1"
    assert_contains "$output" "parallel-repo2" "Function fetches repo2"
    assert_contains "$output" "parallel-repo3" "Function fetches repo3"

    # Parallel execution should be faster than 300ms (3 * 100ms sequential)
    # Allow some margin for test execution overhead
    if test $duration -lt 250
        test_pass "Parallel execution is faster than sequential (${duration}ms)"
    else
        test_fail "Parallel execution may not be working (${duration}ms)" "Expected < 250ms"
    end
end

function test_gita_batch_fetch_timeout_handling
    # Mock gita-repo-discovery to return repositories
    function gita-repo-discovery
        echo "timeout-repo"
    end

    # Mock gita fetch to hang (simulate timeout)
    mock_command "gita" "
        if test \"\$1\" = 'fetch'
            sleep 10  # Long delay to simulate hanging
            echo \"Should not reach here\"
            exit 0
        fi
    "

    # Function should handle timeouts gracefully (if implemented)
    set -l start_time (date +%s)
    set -l output (gita-batch-fetch --timeout 2 2>&1)
    set -l end_time (date +%s)
    set -l duration (math "$end_time - $start_time")

    # Should not wait for the full 10 seconds
    if test $duration -lt 8
        test_pass "Function handles timeout correctly"
    else
        test_fail "Function does not handle timeout" "Took ${duration}s, expected < 8s"
    end
end

function test_gita_batch_fetch_special_repo_names
    # Mock gita-repo-discovery to return repos with special characters
    function gita-repo-discovery
        echo "my-repo"
        echo "my_repo"
        echo "my.repo"
        echo "my-repo-v2.1"
    end

    # Mock gita fetch to handle special characters
    mock_command "gita" "
        if test \"\$1\" = 'fetch'
            echo \"Fetching special repo: \$2\"
            exit 0
        fi
    "

    # Function should handle special characters in repository names
    set -l output (gita-batch-fetch 2>&1)

    assert_contains "$output" "my-repo" "Function handles repo with dash"
    assert_contains "$output" "my_repo" "Function handles repo with underscore"
    assert_contains "$output" "my.repo" "Function handles repo with dot"
    assert_contains "$output" "my-repo-v2.1" "Function handles complex repo name"
end

function test_gita_batch_fetch_discovery_failure
    # Mock gita-repo-discovery to fail
    function gita-repo-discovery
        return 1
    end

    # Function should handle discovery failure gracefully
    set -l output (gita-batch-fetch 2>&1)

    assert_equals "" "$output" "Function handles discovery failure gracefully"
end

# Test runner
function run_all_gita_batch_fetch_tests
    echo "🧪 Running gita-batch-fetch tests..."

    # Load the function under test
    load_functions (dirname (status --current-filename))/../fish/functions

    run_test test_gita_batch_fetch_no_repositories
    run_test test_gita_batch_fetch_single_repository
    run_test test_gita_batch_fetch_multiple_repositories
    run_test test_gita_batch_fetch_with_errors
    run_test test_gita_batch_fetch_silent_mode
    run_test test_gita_batch_fetch_parallel_execution
    run_test test_gita_batch_fetch_timeout_handling
    run_test test_gita_batch_fetch_special_repo_names
    run_test test_gita_batch_fetch_discovery_failure

    test_summary
end

# Run tests if script is executed directly
if test (status --current-filename) = (status --filename)
    run_all_gita_batch_fetch_tests
end