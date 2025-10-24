# Testing Interactive Sudo Commands

## Manual Testing (Required - Outside Container)

Since these changes involve interactive sudo prompts, they CANNOT be tested
inside Docker containers. Manual testing must be performed on a real system.

### Test Cases

1. **Fresh System Without Cached Sudo**
   - Log out and log back in (clears sudo cache)
   - Run: `DOTFILES_ENVIRONMENT=minimal uv run dotfiles-init`
   - Verify: Sudo password prompt appears and is visible
   - Verify: Can type password successfully
   - Verify: Installation proceeds after password entry

2. **Package Installation**
   - After first sudo prompt, subsequent package operations should not prompt
   - Verify: Rich status messages appear cleanly before/after sudo commands
   - Verify: Package installation output flows to terminal

3. **Systemd Service Operations**
   - Verify: `systemctl enable --now <service>` prompts if needed
   - Verify: Password prompt is visible and functional

4. **Error Handling**
   - Test: Enter wrong password
   - Verify: Clear error message, no hidden failures
   - Test: Cancel password prompt (Ctrl+C)
   - Verify: Clean error handling

### Expected Behavior

- ✅ Sudo password prompt visible and functional
- ✅ Rich status messages don't interfere with prompts
- ✅ Package output flows to terminal during installation
- ✅ Clear error messages on failure
- ✅ No "permission denied" or hidden prompt issues

### Regression Testing

Ensure existing non-sudo commands still work:

- Git operations
- NVM/Pyenv installation
- Config symlink creation
- Non-sudo package checks

## Automated Testing (Container-Safe)

Compilation tests verify imports and CLI interfaces:

```bash
make test-compile
```

This does NOT test actual sudo functionality, only that the code compiles
and imports correctly.
