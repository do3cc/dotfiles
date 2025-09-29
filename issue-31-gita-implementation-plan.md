# Issue #31: Add gita multi-repository management tool to init program

## Analysis Summary

**Goal**: Add support for installing `gita`, a CLI tool for managing multiple git repositories, to the dotfiles init program.

## Background Research

`gita` is a Python-based tool that provides:

- Visual status overview of multiple repositories
- Batch operations (pull, push, status) across all repos
- Repository grouping and organization
- Color-coded branch status indicators
- Parallel execution for performance

## Implementation Plan

### Phase 1: Package Installation Integration

1. **Add to pacman_packages list in init.py**
   - Research if `gita` is available in official Arch repos
   - If not, add to AUR packages list for `yay` installation

2. **Add fallback installation method**
   - Add pip-based installation for non-Arch systems
   - Use `uv pip install gita` for consistency with project tooling

3. **Make installation conditional**
   - Add CLI flag or environment variable to control gita installation
   - Don't force installation on all users

### Phase 2: Configuration Integration

1. **Auto-discovery of project directories**
   - Check for common project directories (`~/projects`, `~/dev`, `~/work`)
   - Optionally auto-add discovered directories to gita

2. **Basic configuration setup**
   - Initialize gita configuration if repositories are found
   - Set up reasonable defaults

### Phase 3: Integration Points

1. **Fish shell integration**
   - Consider adding fish functions for common gita operations
   - Integrate with existing git workflow functions

2. **Status integration**
   - Consider integrating gita status into pkgstatus.py output
   - Add multi-repo status to project status tools

## Files to Modify

- `src/dotfiles/init.py` - Add package installation logic
- Potentially `fish/functions/` - Add convenience functions
- Potentially `src/dotfiles/pkgstatus.py` - Add gita status integration

## Testing Requirements

- Test installation on Arch-based systems
- Test fallback installation on other distributions
- Verify gita works correctly after installation
- Test with and without project directories present

## Acceptance Criteria

- [ ] `gita` installs successfully on Arch via AUR
- [ ] Fallback pip installation works on other systems
- [ ] Installation is optional/conditional
- [ ] Basic configuration is set up when appropriate
- [ ] No breaking changes to existing functionality
- [ ] Compilation tests continue to pass

## Research Notes

### Installation Methods

**Arch Linux:**

```bash
# Check if available in official repos
pacman -Ss gita

# Install via AUR
yay -S gita
```

**Other systems:**

```bash
# Python pip installation
pip install gita

# Or using uv (preferred for this project)
uv pip install gita
```

### Basic Usage

```bash
# Add repositories
gita add repo_path

# Show status of all repos
gita ll

# Pull all repos
gita pull

# Custom groups
gita group add mygroup repo1 repo2
```

## Implementation Approach

1. Start with minimal package installation integration
2. Test basic functionality
3. Add optional configuration features
4. Consider advanced integrations based on user feedback

This approach ensures we deliver core functionality while keeping the scope manageable.
