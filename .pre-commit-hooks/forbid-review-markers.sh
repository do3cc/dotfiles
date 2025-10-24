#!/bin/bash
# Pre-commit hook to forbid TODO: REVIEW markers

# Filter out files that document the TODO: REVIEW pattern
files=()
for file in "$@"; do
	# Skip CLAUDE.md and this hook script itself
	if [[ "$file" != "CLAUDE.md" && "$file" != *"forbid-review-markers.sh" ]]; then
		files+=("$file")
	fi
done

# Only check if we have files to check
if [ ${#files[@]} -gt 0 ]; then
	if grep -H "# TODO: REVIEW" "${files[@]}"; then
		echo "❌ Found TODO: REVIEW markers. Remove them before committing."
		exit 1
	fi
fi
