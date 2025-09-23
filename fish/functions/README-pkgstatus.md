# pkgstatus - Package & System Status Checker

A Python-powered tool with Fish shell integration that provides fast startup information about package updates, git repository status, and init script status using intelligent caching.

## Architecture

- **Python Backend** (`pkgstatus.py`): Handles all complex logic, caching, and formatting
- **Fish Wrapper** (`pkgstatus.fish`): Thin wrapper that finds and calls the Python script
- **Configuration** (`pkgstatus-config.fish`): Fish-based configuration management

## Features

- **Package Updates**: Shows available updates across all package managers (via swman.py)
- **Git Repository Status**: Displays uncommitted changes and unpushed commits
- **Init Script Monitoring**: Tracks when dotfiles init script was last run
- **Smart Caching**: Fast startup times with background refresh
- **Configurable**: Multiple display modes and settings

## Usage

```bash
# Show current status (interactive)
pkgstatus

# Only show if issues exist (quiet mode, used in config.fish)
pkgstatus --quiet

# Machine readable JSON output
pkgstatus --json

# Force cache refresh
pkgstatus --refresh

# Show help
pkgstatus --help
```

## Configuration

```bash
# Configuration management
pkgstatus-config                    # Show current settings
pkgstatus-config enable/disable     # Enable/disable entirely
pkgstatus-config startup MODE       # Set startup behavior
pkgstatus-config cache-hours N      # Set cache duration
pkgstatus-config git enable/disable # Git monitoring on/off
pkgstatus-config init enable/disable # Init monitoring on/off
pkgstatus-config clear-cache        # Clear all cached data
pkgstatus-config reset              # Reset to defaults
```

### Startup Modes

- **quiet** (default): Only show output if issues exist
- **always**: Always show status information
- **never**: Never show on startup

## Cache Strategy

- **Packages**: Refreshed every 6 hours (configurable)
- **Git**: Refreshed every 1 hour
- **Init**: Refreshed every 24 hours

Cache files stored in: `$XDG_CACHE_HOME/dotfiles/status/`

## Integration

Automatically integrated into `fish/config.fish` to show status on shell startup in quiet mode. Background processes handle cache updates to keep startup fast (~50ms).

## Example Output

**Quiet Mode** (only if issues):
```
⚠️  51 package updates available (2h ago)
🔄 Git: 3 uncommitted 1 unpushed
```

**Interactive Mode**:
```
📦 Package Status:
   ⚠️  51 updates available (checked 2h ago)
      • pacman: 51 updates

🔄 Git Status:
   📁 Branch: main
   ⚠️  3 uncommitted changes
   ⬆️  1 commits ahead of origin

⚙️  Init Status:
   ✅ Recently run (6h ago)
```

## Requirements

- Fish shell
- jq (JSON processing)
- swman.py (for package status)
- git (for repository status)