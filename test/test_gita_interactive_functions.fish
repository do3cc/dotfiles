#!/usr/bin/env fish

# Tests for interactive gita worktree functions

source (dirname (status --current-filename))/fish_test_framework.fish

# Tests for gita-worktree-status.fish
function test_gita_worktree_status_no_repositories
    # Mock gita-repo-discovery to return no repositories
    function gita-repo-discovery
        echo ""
    end

    # Function should handle empty repository list gracefully
    set -l output (gita-worktree-status 2>&1)

    assert_contains "$output" "No gita repositories with worktrees found" "Function reports no repositories found"
end

function test_gita_worktree_status_with_repositories
    # Mock gita-repo-discovery to return repositories
    function gita-repo-discovery
        echo "repo1"
        echo "repo2"
    end

    # Mock gita-worktree-detect
    function gita-worktree-detect
        test "$argv[1]" = "repo1"  # Only repo1 has worktrees
    end

    # Mock worktree analysis functions
    function gita-worktree-analyze
        switch $argv[1]
            case "repo1"
                echo "  ✅ 3 worktrees, 1 behind main, 0 uncommitted"
        end
    end

    # Function should show detailed status
    set -l output (gita-worktree-status 2>&1)

    assert_contains "$output" "📊 Worktree Status Report" "Function shows header"
    assert_contains "$output" "repo1" "Function shows repo1"
    assert_contains "$output" "3 worktrees" "Function shows worktree count"
    assert_not_contains "$output" "repo2" "Function skips repo2 without worktrees"
end

# Tests for gita-worktree-pull.fish
function test_gita_worktree_pull_no_repositories
    # Mock gita-repo-discovery to return no repositories
    function gita-repo-discovery
        echo ""
    end

    # Function should handle empty repository list gracefully
    set -l output (gita-worktree-pull 2>&1)

    assert_contains "$output" "No gita repositories with worktrees found" "Function reports no repositories found"
end

function test_gita_worktree_pull_up_to_date_repo
    # Mock gita-repo-discovery to return one repository
    function gita-repo-discovery
        echo "up-to-date-repo"
    end

    # Mock gita-worktree-detect to return true
    function gita-worktree-detect
        return 0
    end

    # Mock gita-check-behind to return 0 (up to date)
    function gita-check-behind
        echo "0"
    end

    # Function should report up-to-date status
    set -l output (gita-worktree-pull 2>&1)

    assert_contains "$output" "Repository: up-to-date-repo" "Function shows repository name"
    assert_contains "$output" "Up to date" "Function shows up-to-date status"
end

function test_gita_worktree_pull_behind_repo_no_pull
    # Mock gita-repo-discovery to return one repository
    function gita-repo-discovery
        echo "behind-repo"
    end

    # Mock gita-worktree-detect to return true
    function gita-worktree-detect
        return 0
    end

    # Mock gita-check-behind to return 5 (behind by 5 commits)
    function gita-check-behind
        echo "5"
    end

    # Mock read to simulate user saying no
    function read
        if test "$argv[1]" = "-P"
            echo "n"  # User chooses not to pull
        end
    end

    # Function should offer to pull but not execute
    set -l output (gita-worktree-pull 2>&1)

    assert_contains "$output" "Behind by 5 commits" "Function shows behind count"
    assert_not_contains "$output" "Running: gita pull" "Function does not pull when user says no"
end

# Tests for gita-worktree-cleanup.fish
function test_gita_worktree_cleanup_no_issues
    # Mock gita-repo-discovery to return repositories
    function gita-repo-discovery
        echo "clean-repo"
    end

    # Mock gita-worktree-detect to return true
    function gita-worktree-detect
        return 0
    end

    # Mock gita-worktree-detect-issues to return no issues
    function gita-worktree-detect-issues
        echo ""
    end

    # Function should report no cleanup needed
    set -l output (gita-worktree-cleanup 2>&1)

    assert_contains "$output" "🧹 Worktree Cleanup Analysis" "Function shows header"
    assert_contains "$output" "No cleanup actions needed" "Function reports no cleanup needed"
end

function test_gita_worktree_cleanup_with_issues
    # Mock gita-repo-discovery to return repositories
    function gita-repo-discovery
        echo "messy-repo"
    end

    # Mock gita-worktree-detect to return true
    function gita-worktree-detect
        return 0
    end

    # Mock gita-worktree-detect-issues to return cleanup commands
    function gita-worktree-detect-issues
        echo "gita worktree remove messy-repo old-feature"
        echo "gita branch delete messy-repo merged-branch"
    end

    # Function should show cleanup commands
    set -l output (gita-worktree-cleanup 2>&1)

    assert_contains "$output" "Repository: messy-repo" "Function shows repository name"
    assert_contains "$output" "gita worktree remove" "Function shows worktree removal command"
    assert_contains "$output" "gita branch delete" "Function shows branch deletion command"
end

# Tests for gita-worktree-audit.fish
function test_gita_worktree_audit_comprehensive_report
    # Mock gita-repo-discovery to return multiple repositories
    function gita-repo-discovery
        echo "repo1"
        echo "repo2"
        echo "repo3"
    end

    # Mock gita-worktree-detect
    function gita-worktree-detect
        switch $argv[1]
            case "repo1" "repo3"
                return 0  # Have worktrees
            case "repo2"
                return 1  # No worktrees
        end
    end

    # Mock audit analysis functions
    function gita-worktree-audit-repo
        switch $argv[1]
            case "repo1"
                echo "  📊 5 worktrees total"
                echo "  ⚠️  2 worktrees need attention"
                echo "  🔧 3 cleanup actions available"
            case "repo3"
                echo "  📊 2 worktrees total"
                echo "  ✅ All worktrees healthy"
        end
    end

    # Function should provide comprehensive audit
    set -l output (gita-worktree-audit 2>&1)

    assert_contains "$output" "🔍 Comprehensive Worktree Audit" "Function shows audit header"
    assert_contains "$output" "Repository: repo1" "Function audits repo1"
    assert_contains "$output" "5 worktrees total" "Function shows repo1 details"
    assert_contains "$output" "Repository: repo3" "Function audits repo3"
    assert_contains "$output" "All worktrees healthy" "Function shows repo3 status"
    assert_not_contains "$output" "Repository: repo2" "Function skips repo2 without worktrees"
end

# Tests for helper functions
function test_gita_check_behind_function
    # Mock gita to return behind count
    mock_command "gita" "
        if test \"\$1\" = 'log' -a \"\$2\" = '--oneline'
            echo 'abc123 Recent commit'
            echo 'def456 Another commit'
            echo 'ghi789 Third commit'
        fi
    "

    # Function should return correct behind count
    set -l count (gita-check-behind test-repo)

    assert_equals "3" "$count" "Function returns correct behind count"
end

function test_gita_worktree_detect_issues_function
    # Mock git commands for issue detection
    mock_command "git" "
        case \"\$1\" in
            'branch')
                echo '* main'
                echo '  feature-merged'
                echo '  feature-active'
                ;;
            'merge-base')
                echo 'abc123'
                ;;
            'rev-parse')
                case \"\$2\" in
                    'feature-merged')
                        echo 'abc123'  # Same as merge-base - merged
                        ;;
                    'feature-active')
                        echo 'def456'  # Different - not merged
                        ;;
                esac
                ;;
        esac
    "

    # Mock gita to get repository path
    mock_command "gita" "
        if test \"\$1\" = 'll'
            echo '/home/user/test-repo'
        fi
    "

    # Function should detect merged branches
    set -l issues (gita-worktree-detect-issues test-repo)

    assert_contains "$issues" "feature-merged" "Function detects merged branch"
    assert_not_contains "$issues" "feature-active" "Function ignores active branch"
end

# Test runner for all interactive functions
function run_all_gita_interactive_tests
    echo "🧪 Running gita interactive functions tests..."

    # Load the functions under test
    load_functions (dirname (status --current-filename))/../fish/functions

    # gita-worktree-status tests
    run_test test_gita_worktree_status_no_repositories
    run_test test_gita_worktree_status_with_repositories

    # gita-worktree-pull tests
    run_test test_gita_worktree_pull_no_repositories
    run_test test_gita_worktree_pull_up_to_date_repo
    run_test test_gita_worktree_pull_behind_repo_no_pull

    # gita-worktree-cleanup tests
    run_test test_gita_worktree_cleanup_no_issues
    run_test test_gita_worktree_cleanup_with_issues

    # gita-worktree-audit tests
    run_test test_gita_worktree_audit_comprehensive_report

    # Helper function tests
    run_test test_gita_check_behind_function
    run_test test_gita_worktree_detect_issues_function

    test_summary
end

# Run tests if script is executed directly
if test (status --current-filename) = (status --filename)
    run_all_gita_interactive_tests
end