# Issue #20 Implementation Plan: Fix pkgstatus/swman incorrectly installing packages on shell startup

## Problem Analysis

### What exactly is happening

1. **Shell Startup Flow**: Every Fish shell startup executes `pkgstatus --quiet` (line 23 in `/fish/config.fish`)
2. **Call Chain**: `pkgstatus --quiet` → `dotfiles-pkgstatus --quiet` → `swman.py --check --json` → `manager.check_updates()` for each package manager
3. **Reported Issue**: Packages are being **installed** during this process, not just checked for updates
4. **Timing Problem**: Once packages are updated, running the command again won't reproduce the issue since packages are already current

### Current Problematic Behavior

The `--check` flag is supposed to be read-only but currently:

- Some package managers cannot actually check for updates but return `(True, 0)` anyway
- These false positives may trigger unintended downstream behavior
- In quiet mode, tools without update checking capability should be silently skipped but aren't

## Root Cause Analysis

### Primary Suspect: Faulty check_updates() Implementations

The issue likely stems from problematic `check_updates()` methods in `/src/dotfiles/swman.py`:

```python
# UvToolsManager.check_updates() - Line 263-266
def check_updates(self) -> Tuple[bool, int]:
    # UV doesn't have a direct "check updates" command
    # We'd need to parse `uv tool list` and check each tool
    return True, 0  # Assume updates available for now

# LazyNvimManager.check_updates() - Line 324-326
def check_updates(self) -> Tuple[bool, int]:
    # Lazy.nvim has automatic checking enabled in your config
    return True, 0  # Assume updates available

# FisherManager.check_updates() - Line 378-379
def check_updates(self) -> Tuple[bool, int]:
    return True, 0  # Assume updates available
```

### Potential Installation Triggers

1. **False Update Signals**: Returning `(True, 0)` may trigger other code paths that attempt installations
2. **Missing Dry-Run Logic**: Some update methods may not properly respect dry-run mode
3. **Cache Refresh Side Effects**: The cache refresh process in `pkgstatus.py` may inadvertently trigger updates

### Architecture Issue

The current design conflates "can check for updates" with "has updates available":

- Managers that can't check return `(True, 0)` (false positive)
- This creates noise in quiet mode and may trigger unintended behavior
- No distinction between "updates available" vs "cannot determine"

## Solution Approach

### 1. Implement Proper Read-Only Checking

**Create a three-state update status system:**

```python
class UpdateCheckResult(Enum):
    NO_UPDATES = "no_updates"           # Definitely no updates
    UPDATES_AVAILABLE = "updates_available"  # Updates confirmed available
    CANNOT_DETERMINE = "cannot_determine"    # Manager can't check
```

### 2. Silent Handling for Incapable Managers

In quiet mode:

- Managers returning `CANNOT_DETERMINE` are silently skipped (no output)
- Only `UPDATES_AVAILABLE` results generate warnings
- In normal mode, show informational notes about managers that can't check

### 3. Enforce True Read-Only Behavior

- Audit all `check_updates()` methods to ensure no installation commands
- Add explicit dry-run validation
- Implement proper update checking for UV tools and other managers where possible

## Implementation Steps

### Step 1: Fix swman.py Package Manager Check Methods

**File: `/src/dotfiles/swman.py`**

1. **Replace problematic check_updates() methods:**

   ```python
   # UvToolsManager.check_updates()
   def check_updates(self) -> Tuple[bool, int]:
       # Return cannot_determine status instead of false positive
       return False, -1  # -1 indicates "cannot determine"
   ```

2. **Implement proper checking where possible:**
   ```python
   # UvToolsManager - attempt actual checking
   def check_updates(self) -> Tuple[bool, int]:
       try:
           result = subprocess.run(
               ["uv", "tool", "list"], capture_output=True, text=True, timeout=10
           )
           if result.returncode == 0:
               # Parse output to detect outdated tools
               # Return actual count if possible, or (False, -1) if cannot determine
               return False, -1  # For now, cannot determine
       except Exception:
           return False, -1
   ```

### Step 2: Update pkgstatus.py to Handle Indeterminate States

**File: `/src/dotfiles/pkgstatus.py`**

1. **Modify `_refresh_packages_cache()` method** (line 126):
   - Handle managers that return `(-1)` count (cannot determine)
   - Don't include them in total update counts
   - Mark them as "indeterminate" in cache

2. **Update output formatting methods:**
   - `format_quiet_output()` - skip indeterminate managers in quiet mode
   - `format_interactive_output()` - show informational notes in normal mode

### Step 3: Audit All Update Execution Paths

**Files: `/src/dotfiles/swman.py`, `/src/dotfiles/pkgstatus.py`**

1. **Verify `--check` flag isolation:**
   - Ensure `orchestrator.check_all()` only calls `check_updates()` methods
   - Never calls `update()` methods when `--check` flag is used
   - Add explicit guards against accidental update execution

2. **Add logging for debugging:**
   - Log all commands executed during check operations
   - Track which managers report updates vs cannot determine
   - Monitor for any unexpected installation commands

### Step 4: Implement Enhanced Quiet Mode

**File: `/src/dotfiles/pkgstatus.py`**

1. **Modify quiet output logic:**

   ```python
   def format_quiet_output(self, status: StatusResult) -> str:
       messages = []
       pkg_data = status.packages

       # Only show managers with confirmed updates
       confirmed_updates = {}
       for manager, info in pkg_data.get("packages", {}).items():
           if info.get("count", 0) > 0:  # Positive count = confirmed updates
               confirmed_updates[manager] = info

       total_confirmed = sum(info.get("count", 0) for info in confirmed_updates.values())
       if total_confirmed > 0:
           messages.append(f"⚠️  {total_confirmed} package updates available")
   ```

### Step 5: Add Comprehensive Logging

**Files: `/src/dotfiles/swman.py`, `/src/dotfiles/pkgstatus.py`**

1. **Log all check operations:**

   ```python
   logger.log_info("checking_package_manager",
                   manager=manager.name,
                   command="check_updates")
   ```

2. **Log manager capabilities:**
   ```python
   logger.log_info("manager_check_result",
                   manager=manager.name,
                   can_check=count >= 0,
                   has_updates=has_updates,
                   count=count)
   ```

## Testing Strategy

### 1. Reproduction Testing

**Create a test environment that reproduces the original issue:**

```bash
# Set up a fresh shell session
export SHELL=/usr/bin/fish
fish -c "pkgstatus --quiet"
# Monitor for any package installation commands
```

### 2. Unit Testing for Package Managers

**Test each manager's check_updates() method:**

```python
def test_uv_tools_check_only():
    manager = UvToolsManager()
    if manager.is_available():
        # Should not install anything
        before_state = get_uv_tool_state()
        result = manager.check_updates()
        after_state = get_uv_tool_state()
        assert before_state == after_state  # No changes
```

### 3. Integration Testing

**Test the complete shell startup flow:**

```bash
# Test quiet mode behavior
dotfiles-pkgstatus --quiet

# Test normal mode behavior
dotfiles-pkgstatus

# Test direct swman check
dotfiles-swman --check --json
```

### 4. Regression Testing

**Ensure fix doesn't break existing functionality:**

```bash
# Test legitimate update operations still work
dotfiles-swman --system --dry-run
dotfiles-swman --tools --dry-run

# Test cache refresh behavior
dotfiles-pkgstatus --refresh
```

## Open Questions

### 1. UV Tools Update Checking

**Question:** Can UV tools provide meaningful update checking without triggering installations?

**Investigation needed:**

- Research `uv tool list` output format
- Determine if tools can be checked for updates without modifying them
- Consider implementing proper checking vs marking as indeterminate

### 2. Neovim Plugin Update Detection

**Question:** Can Lazy.nvim check for updates without auto-updating?

**Investigation needed:**

- Review Lazy.nvim API for read-only update checking
- Test if `--headless` commands trigger installations
- Determine appropriate read-only checking approach

### 3. Fish Plugin Update Checking

**Question:** Does Fisher have read-only update checking capabilities?

**Investigation needed:**

- Review Fisher documentation for check-only commands
- Test Fisher's behavior when checking for updates
- Implement proper checking if available

### 4. Cache Staleness vs Silent Failures

**Question:** How should the system handle managers that cannot provide update information?

**Decision needed:**

- Should these be cached as "unknown" state?
- How long should "cannot determine" results be cached?
- Should there be different cache durations for different manager types?

### 5. Backwards Compatibility

**Question:** Will changing the return format of check_updates() break existing integrations?

**Investigation needed:**

- Review all callers of check_updates() methods
- Ensure pkgstatus fish function continues to work
- Verify JSON output format remains compatible

## Success Criteria

### 1. No Unintended Installations

- Shell startup with `pkgstatus --quiet` performs zero package installations
- All `--check` operations are truly read-only
- Comprehensive logging confirms no installation commands executed

### 2. Proper Quiet Mode Behavior

- Managers that cannot check for updates are silently skipped in quiet mode
- Only confirmed available updates generate output in quiet mode
- Normal mode shows informational notes about incapable managers

### 3. Improved Accuracy

- Package managers only report updates when they can actually confirm them
- No false positives from managers that cannot check
- Clear distinction between "no updates", "updates available", and "cannot determine"

### 4. Maintainable Architecture

- Clear separation between checking and updating operations
- Comprehensive logging for debugging and monitoring
- Extensible design for adding new package managers

This implementation plan addresses the root cause of the issue while improving the overall architecture and user experience of the package status system.
