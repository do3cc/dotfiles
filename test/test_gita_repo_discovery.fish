#!/usr/bin/env fish

# Tests for gita-repo-discovery.fish

source (dirname (status --current-filename))/fish_test_framework.fish

function test_gita_repo_discovery_command_not_available
    # Mock gita command to not exist
    mock_command "gita" "exit 127"

    # Function should return 1 when gita is not available
    gita-repo-discovery
    assert_false "Function returns 1 when gita command is not available"
end

function test_gita_repo_discovery_with_repo_path_file
    # Mock gita command to exist
    mock_command "gita" "echo 'gita mock command'"

    # Create test repo_path file
    create_test_file "$TEST_CONFIG_DIR/gita/repo_path" "dotfiles:/home/user/dotfiles
project1:/home/user/project1
project2:/home/user/project2

"

    # Function should parse repo names from repo_path file
    set -l output (gita-repo-discovery)

    assert_contains "$output" "dotfiles" "Output contains 'dotfiles' repo"
    assert_contains "$output" "project1" "Output contains 'project1' repo"
    assert_contains "$output" "project2" "Output contains 'project2' repo"
    assert_not_contains "$output" "/home/user" "Output does not contain paths"
end

function test_gita_repo_discovery_with_repo_path_file_empty_lines
    # Mock gita command to exist
    mock_command "gita" "echo 'gita mock command'"

    # Create test repo_path file with empty lines
    create_test_file "$TEST_CONFIG_DIR/gita/repo_path" "
dotfiles:/home/user/dotfiles

project1:/home/user/project1


project2:/home/user/project2

"

    # Function should filter out empty lines
    set -l output (gita-repo-discovery)
    set -l lines (echo "$output" | wc -l)

    assert_equals "3" "$lines" "Should return exactly 3 non-empty lines"
    assert_contains "$output" "dotfiles" "Output contains 'dotfiles' repo"
    assert_contains "$output" "project1" "Output contains 'project1' repo"
    assert_contains "$output" "project2" "Output contains 'project2' repo"
end

function test_gita_repo_discovery_no_repo_path_file
    # Mock gita command to exist and return repo list
    mock_command "gita" "echo 'fallback-repo1
fallback-repo2
fallback-repo3'"

    # No repo_path file exists - should use gita list fallback
    set -l output (gita-repo-discovery)

    assert_contains "$output" "fallback-repo1" "Output contains 'fallback-repo1' from gita list"
    assert_contains "$output" "fallback-repo2" "Output contains 'fallback-repo2' from gita list"
    assert_contains "$output" "fallback-repo3" "Output contains 'fallback-repo3' from gita list"
end

function test_gita_repo_discovery_gita_list_with_empty_lines
    # Mock gita command to return list with empty lines
    mock_command "gita" "echo '
repo1

repo2


repo3
'"

    # Should filter out empty lines from gita list output
    set -l output (gita-repo-discovery)
    set -l lines (echo "$output" | wc -l)

    assert_equals "3" "$lines" "Should return exactly 3 non-empty lines from gita list"
    assert_contains "$output" "repo1" "Output contains 'repo1'"
    assert_contains "$output" "repo2" "Output contains 'repo2'"
    assert_contains "$output" "repo3" "Output contains 'repo3'"
end

function test_gita_repo_discovery_gita_list_error
    # Mock gita command to return error
    mock_command "gita" "echo 'Error: No repositories found' >&2; exit 1"

    # Should handle gita list errors gracefully
    set -l output (gita-repo-discovery)

    assert_equals "" "$output" "Should return empty output when gita list fails"
end

function test_gita_repo_discovery_repo_path_special_characters
    # Mock gita command to exist
    mock_command "gita" "echo 'gita mock command'"

    # Create test repo_path file with special characters in repo names
    create_test_file "$TEST_CONFIG_DIR/gita/repo_path" "my-project:/home/user/my-project
my_project:/home/user/my_project
my.project:/home/user/my.project"

    # Function should handle special characters in repo names
    set -l output (gita-repo-discovery)

    assert_contains "$output" "my-project" "Output contains repo with dash"
    assert_contains "$output" "my_project" "Output contains repo with underscore"
    assert_contains "$output" "my.project" "Output contains repo with dot"
end

function test_gita_repo_discovery_repo_path_colon_in_path
    # Mock gita command to exist
    mock_command "gita" "echo 'gita mock command'"

    # Create test repo_path file with colon in path (edge case)
    create_test_file "$TEST_CONFIG_DIR/gita/repo_path" "repo1:/home/user/path:with:colons/repo1
repo2:/home/user/normal/repo2"

    # Function should handle paths with colons correctly (split on first colon only)
    set -l output (gita-repo-discovery)

    assert_contains "$output" "repo1" "Output contains 'repo1'"
    assert_contains "$output" "repo2" "Output contains 'repo2'"
    assert_not_contains "$output" "with" "Output does not contain path fragments"
end

# Test runner
function run_all_gita_repo_discovery_tests
    echo "🧪 Running gita-repo-discovery tests..."

    # Load the function under test
    load_functions (dirname (status --current-filename))/../fish/functions

    run_test test_gita_repo_discovery_command_not_available
    run_test test_gita_repo_discovery_with_repo_path_file
    run_test test_gita_repo_discovery_with_repo_path_file_empty_lines
    run_test test_gita_repo_discovery_no_repo_path_file
    run_test test_gita_repo_discovery_gita_list_with_empty_lines
    run_test test_gita_repo_discovery_gita_list_error
    run_test test_gita_repo_discovery_repo_path_special_characters
    run_test test_gita_repo_discovery_repo_path_colon_in_path

    test_summary
end

# Run tests if script is executed directly
if test (status --current-filename) = (status --filename)
    run_all_gita_repo_discovery_tests
end