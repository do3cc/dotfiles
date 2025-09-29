#!/usr/bin/env fish

# Tests for gita-worktree-detect.fish

source (dirname (status --current-filename))/fish_test_framework.fish

function test_gita_worktree_detect_no_arguments
    # Function should return 1 when no repository is provided
    gita-worktree-detect
    assert_false "Function returns 1 when no repository argument provided"
end

function test_gita_worktree_detect_repo_with_worktrees
    # Mock git worktree list to return multiple worktrees
    mock_command "git" "echo '/home/user/dotfiles                          abcd123 [main]
/home/user/dotfiles/worktrees/feature/test  efgh456 [feature-branch]
/home/user/dotfiles/worktrees/review/pr-1   ijkl789 [review-branch]'"

    # Mock gita to return repo path
    mock_command "gita" "
        if test \"\$1\" = 'll' -a \"\$2\" = 'test-repo'
            echo '/home/user/dotfiles'
        else
            echo 'gita: unknown command or option'
            exit 1
        fi
    "

    # Function should return 0 (true) for repo with worktrees
    gita-worktree-detect test-repo
    assert_true "Function returns 0 for repository with worktrees"
end

function test_gita_worktree_detect_repo_without_worktrees
    # Mock git worktree list to return only main repository
    mock_command "git" "echo '/home/user/simple-repo  abcd123 [main]'"

    # Mock gita to return repo path
    mock_command "gita" "
        if test \"\$1\" = 'll' -a \"\$2\" = 'simple-repo'
            echo '/home/user/simple-repo'
        else
            echo 'gita: unknown command or option'
            exit 1
        fi
    "

    # Function should return 1 (false) for repo without worktrees
    gita-worktree-detect simple-repo
    assert_false "Function returns 1 for repository without worktrees"
end

function test_gita_worktree_detect_git_worktree_error
    # Mock git worktree list to fail
    mock_command "git" "echo 'fatal: not a git repository' >&2; exit 128"

    # Mock gita to return repo path
    mock_command "gita" "
        if test \"\$1\" = 'll' -a \"\$2\" = 'invalid-repo'
            echo '/home/user/invalid-repo'
        else
            echo 'gita: unknown command or option'
            exit 1
        fi
    "

    # Function should return 1 when git worktree list fails
    gita-worktree-detect invalid-repo
    assert_false "Function returns 1 when git worktree list fails"
end

function test_gita_worktree_detect_gita_repo_not_found
    # Mock gita to not find the repository
    mock_command "gita" "echo 'gita: repository not found' >&2; exit 1"

    # Function should return 1 when gita can't find the repo
    gita-worktree-detect nonexistent-repo
    assert_false "Function returns 1 when gita cannot find repository"
end

function test_gita_worktree_detect_empty_git_output
    # Mock git worktree list to return empty output
    mock_command "git" "echo ''"

    # Mock gita to return repo path
    mock_command "gita" "
        if test \"\$1\" = 'll' -a \"\$2\" = 'empty-repo'
            echo '/home/user/empty-repo'
        else
            echo 'gita: unknown command or option'
            exit 1
        fi
    "

    # Function should return 1 for empty git worktree output
    gita-worktree-detect empty-repo
    assert_false "Function returns 1 when git worktree list returns empty output"
end

function test_gita_worktree_detect_worktree_count_edge_cases
    # Test with exactly 2 lines (1 main + 1 worktree = has worktrees)
    mock_command "git" "echo '/home/user/repo  abcd123 [main]
/home/user/repo/worktrees/feature  efgh456 [feature]'"

    mock_command "gita" "
        if test \"\$1\" = 'll' -a \"\$2\" = 'edge-repo'
            echo '/home/user/repo'
        else
            echo 'gita: unknown command or option'
            exit 1
        fi
    "

    # Should return 0 (true) with exactly one worktree
    gita-worktree-detect edge-repo
    assert_true "Function returns 0 for repository with exactly one worktree"
end

function test_gita_worktree_detect_whitespace_in_paths
    # Mock git worktree list with paths containing spaces
    mock_command "git" "echo '/home/user/my project                     abcd123 [main]
/home/user/my project/worktrees/feature test  efgh456 [feature-test]'"

    # Mock gita to return repo path with spaces
    mock_command "gita" "
        if test \"\$1\" = 'll' -a \"\$2\" = 'space-repo'
            echo '/home/user/my project'
        else
            echo 'gita: unknown command or option'
            exit 1
        fi
    "

    # Function should handle paths with spaces correctly
    gita-worktree-detect space-repo
    assert_true "Function handles repository paths with spaces correctly"
end

function test_gita_worktree_detect_multiple_worktrees
    # Mock git worktree list with many worktrees
    mock_command "git" "echo '/home/user/big-project                     abcd123 [main]
/home/user/big-project/worktrees/feature/f1    efgh456 [feature-1]
/home/user/big-project/worktrees/feature/f2    ijkl789 [feature-2]
/home/user/big-project/worktrees/review/pr-1   mnop012 [review-1]
/home/user/big-project/worktrees/review/pr-2   qrst345 [review-2]
/home/user/big-project/worktrees/bugfix/b1     uvwx678 [bugfix-1]'"

    # Mock gita to return repo path
    mock_command "gita" "
        if test \"\$1\" = 'll' -a \"\$2\" = 'big-repo'
            echo '/home/user/big-project'
        else
            echo 'gita: unknown command or option'
            exit 1
        fi
    "

    # Function should return 0 for repo with multiple worktrees
    gita-worktree-detect big-repo
    assert_true "Function returns 0 for repository with multiple worktrees"
end

function test_gita_worktree_detect_special_characters_in_repo_name
    # Mock git worktree list
    mock_command "git" "echo '/home/user/my-repo_v2.1                   abcd123 [main]
/home/user/my-repo_v2.1/worktrees/feature      efgh456 [feature]'"

    # Mock gita to handle special characters in repo name
    mock_command "gita" "
        if test \"\$1\" = 'll' -a \"\$2\" = 'my-repo_v2.1'
            echo '/home/user/my-repo_v2.1'
        else
            echo 'gita: unknown command or option'
            exit 1
        fi
    "

    # Function should handle special characters in repository names
    gita-worktree-detect my-repo_v2.1
    assert_true "Function handles special characters in repository name"
end

# Test runner
function run_all_gita_worktree_detect_tests
    echo "🧪 Running gita-worktree-detect tests..."

    # Load the function under test
    load_functions (dirname (status --current-filename))/../fish/functions

    run_test test_gita_worktree_detect_no_arguments
    run_test test_gita_worktree_detect_repo_with_worktrees
    run_test test_gita_worktree_detect_repo_without_worktrees
    run_test test_gita_worktree_detect_git_worktree_error
    run_test test_gita_worktree_detect_gita_repo_not_found
    run_test test_gita_worktree_detect_empty_git_output
    run_test test_gita_worktree_detect_worktree_count_edge_cases
    run_test test_gita_worktree_detect_whitespace_in_paths
    run_test test_gita_worktree_detect_multiple_worktrees
    run_test test_gita_worktree_detect_special_characters_in_repo_name

    test_summary
end

# Run tests if script is executed directly
if test (status --current-filename) = (status --filename)
    run_all_gita_worktree_detect_tests
end