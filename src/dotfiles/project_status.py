#!/usr/bin/env python3
# pyright: strict
"""
Project Status Tool for Dotfiles Repository

Provides comprehensive status overview including:
- Open GitHub issues and PRs
- Local branches and worktrees
- Recent commits and activity
- Work in progress indicators
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .logging_config import setup_logging


@dataclass
class IssueInfo:
    """GitHub issue information"""

    number: int
    title: str
    state: str
    labels: List[str]
    assignee: Optional[str]
    url: str


@dataclass
class PRInfo:
    """GitHub pull request information"""

    number: int
    title: str
    state: str
    branch: str
    base: str
    draft: bool
    url: str


@dataclass
class BranchInfo:
    """Git branch information"""

    name: str
    commit: str
    ahead: int
    behind: int
    last_commit_date: str
    has_worktree: bool
    worktree_path: Optional[str]


@dataclass
class WorktreeInfo:
    """Git worktree information"""

    path: str
    branch: str
    commit: str
    has_uncommitted: bool
    type_category: str  # review, feature, bugfix, experimental


class ProjectStatusChecker:
    """Main class for checking project status"""

    def __init__(self):
        self.logger = setup_logging("project_status")

    def get_github_issues(self) -> List[IssueInfo]:
        """Fetch open GitHub issues"""
        self.logger.log_info("fetching GitHub issues")

        try:
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "list",
                    "--json",
                    "number,title,state,labels,assignees,url",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.logger.log_subprocess_result(
                "fetch GitHub issues", ["gh", "issue", "list"], result
            )

            if result.returncode != 0:
                self.logger.log_error(
                    "failed to fetch GitHub issues", error=result.stderr
                )
                return []

            issues_data: List[Any] = json.loads(result.stdout)
            issues: List[IssueInfo] = []

            for issue in issues_data:
                assignee = None
                if issue.get("assignees"):
                    assignee = issue["assignees"][0].get("login")

                labels = [label["name"] for label in issue.get("labels", [])]

                issues.append(
                    IssueInfo(
                        number=issue["number"],
                        title=issue["title"],
                        state=issue["state"],
                        labels=labels,
                        assignee=assignee,
                        url=issue["url"],
                    )
                )

            self.logger.log_info("fetched GitHub issues", count=len(issues))
            return issues

        except Exception as e:
            self.logger.log_error("error fetching GitHub issues", error=str(e))
            return []

    def get_github_prs(self) -> List[PRInfo]:
        """Fetch open GitHub pull requests"""
        self.logger.log_info("fetching GitHub pull requests")

        try:
            result = subprocess.run(
                [
                    "gh",
                    "pr",
                    "list",
                    "--json",
                    "number,title,state,headRefName,baseRefName,isDraft,url",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.logger.log_subprocess_result(
                "fetch GitHub PRs", ["gh", "pr", "list"], result
            )

            if result.returncode != 0:
                self.logger.log_error("failed to fetch GitHub PRs", error=result.stderr)
                return []

            prs_data: List[Any] = json.loads(result.stdout)
            prs: List[PRInfo] = []

            for pr in prs_data:
                prs.append(
                    PRInfo(
                        number=pr["number"],
                        title=pr["title"],
                        state=pr["state"],
                        branch=pr["headRefName"],
                        base=pr["baseRefName"],
                        draft=pr["isDraft"],
                        url=pr["url"],
                    )
                )

            self.logger.log_info("fetched GitHub PRs", count=len(prs))
            return prs

        except Exception as e:
            self.logger.log_error("error fetching GitHub PRs", error=str(e))
            return []

    def get_local_branches(self) -> List[BranchInfo]:
        """Get information about local branches"""
        self.logger.log_info("analyzing local branches")

        try:
            # Get branch info with tracking information
            result = subprocess.run(
                [
                    "git",
                    "for-each-ref",
                    "--format=%(refname:short)|%(objectname:short)|%(committerdate:iso)|%(upstream:trackshort)",
                    "refs/heads/",
                ],
                capture_output=True,
                text=True,
            )

            self.logger.log_subprocess_result(
                "get branch info", ["git", "for-each-ref"], result
            )

            if result.returncode != 0:
                self.logger.log_error("failed to get branch info", error=result.stderr)
                return []

            branches: List[BranchInfo] = []
            worktrees = self.get_worktrees()
            worktree_branches: Dict[str, WorktreeInfo] = {
                wt.branch: wt for wt in worktrees
            }

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) < 3:
                    continue

                branch_name = parts[0]
                commit = parts[1]
                date = parts[2]
                tracking = parts[3] if len(parts) > 3 else ""

                # Parse ahead/behind info
                ahead, behind = 0, 0
                if tracking:
                    if ">" in tracking:
                        ahead = tracking.count(">")
                    if "<" in tracking:
                        behind = tracking.count("<")

                # Check if branch has worktree
                has_worktree = branch_name in worktree_branches
                worktree_path = (
                    worktree_branches[branch_name].path if has_worktree else None
                )

                branches.append(
                    BranchInfo(
                        name=branch_name,
                        commit=commit,
                        ahead=ahead,
                        behind=behind,
                        last_commit_date=date,
                        has_worktree=has_worktree,
                        worktree_path=worktree_path,
                    )
                )

            self.logger.log_info("analyzed local branches", count=len(branches))
            return branches

        except Exception as e:
            self.logger.log_error("error analyzing branches", error=str(e))
            return []

    def get_worktrees(self) -> List[WorktreeInfo]:
        """Get information about git worktrees"""
        self.logger.log_info("analyzing worktrees")

        try:
            result = subprocess.run(
                ["git", "worktree", "list", "--porcelain"],
                capture_output=True,
                text=True,
            )

            self.logger.log_subprocess_result(
                "get worktree info", ["git", "worktree", "list"], result
            )

            if result.returncode != 0:
                self.logger.log_error(
                    "failed to get worktree info", error=result.stderr
                )
                return []

            worktrees: List[WorktreeInfo] = []
            current_worktree: Dict[str, Any] = {}

            for line in result.stdout.strip().split("\n"):
                if not line:
                    if current_worktree:
                        worktrees.append(self._process_worktree_info(current_worktree))
                        current_worktree = {}
                    continue

                if line.startswith("worktree "):
                    current_worktree["path"] = line[9:]  # Remove 'worktree ' prefix
                elif line.startswith("HEAD "):
                    current_worktree["commit"] = line[5:][:7]  # Short commit hash
                elif line.startswith("branch "):
                    current_worktree["branch"] = line[7:]  # Remove 'branch ' prefix
                elif line == "bare":
                    current_worktree["bare"] = True
                elif line == "detached":
                    current_worktree["detached"] = True

            # Process last worktree if exists
            if current_worktree:
                worktrees.append(self._process_worktree_info(current_worktree))

            self.logger.log_info("analyzed worktrees", count=len(worktrees))
            return worktrees

        except Exception as e:
            self.logger.log_error("error analyzing worktrees", error=str(e))
            return []

    def _process_worktree_info(self, wt_data: Dict[str, Any]) -> WorktreeInfo:
        """Process raw worktree data into WorktreeInfo object"""
        path: str = wt_data.get("path", "")
        branch: str = wt_data.get("branch", "detached")
        commit: str = wt_data.get("commit", "unknown")

        # Determine type category from path
        type_category: str = "main"
        if "worktrees/" in path:
            path_parts: List[str] = path.split("worktrees/")
            if len(path_parts) > 1:
                remaining: str = path_parts[1]
                if "/" in remaining:
                    type_category = remaining.split("/")[0]

        # Check for uncommitted changes
        has_uncommitted: bool = False
        try:
            if not wt_data.get("bare", False):
                result = subprocess.run(
                    ["git", "-C", path, "status", "--porcelain"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                has_uncommitted = bool(result.stdout.strip())
        except Exception:
            pass  # Ignore errors checking status

        return WorktreeInfo(
            path=path,
            branch=branch,
            commit=commit,
            has_uncommitted=has_uncommitted,
            type_category=type_category,
        )

    def format_status_report(
        self,
        issues: List[IssueInfo],
        prs: List[PRInfo],
        branches: List[BranchInfo],
        worktrees: List[WorktreeInfo],
        format_type: str = "text",
    ) -> str:
        """Format the status report"""

        if format_type == "json":
            return self._format_json_report(issues, prs, branches, worktrees)
        else:
            return self._format_text_report(issues, prs, branches, worktrees)

    def _format_text_report(
        self,
        issues: List[IssueInfo],
        prs: List[PRInfo],
        branches: List[BranchInfo],
        worktrees: List[WorktreeInfo],
    ) -> str:
        """Format as human-readable text report"""

        lines: List[str] = []
        lines.append("🔍 DOTFILES PROJECT STATUS")
        lines.append("=" * 50)
        lines.append("")

        # GitHub Issues
        lines.append(f"📋 OPEN ISSUES ({len(issues)})")
        lines.append("-" * 20)
        if issues:
            for issue in issues:
                labels_str = f" [{', '.join(issue.labels)}]" if issue.labels else ""
                assignee_str = f" (@{issue.assignee})" if issue.assignee else ""
                lines.append(
                    f"  #{issue.number}: {issue.title}{labels_str}{assignee_str}"
                )
        else:
            lines.append("  No open issues")
        lines.append("")

        # Pull Requests
        lines.append(f"🔀 OPEN PULL REQUESTS ({len(prs)})")
        lines.append("-" * 25)
        if prs:
            for pr in prs:
                draft_str = " [DRAFT]" if pr.draft else ""
                lines.append(
                    f"  #{pr.number}: {pr.title} ({pr.branch} → {pr.base}){draft_str}"
                )
        else:
            lines.append("  No open pull requests")
        lines.append("")

        # Worktrees
        lines.append(
            f"🌳 ACTIVE WORKTREES ({len([wt for wt in worktrees if wt.type_category != 'main'])})"
        )
        lines.append("-" * 22)
        organized_worktrees = [wt for wt in worktrees if wt.type_category != "main"]
        if organized_worktrees:
            # Group by type
            by_type: Dict[str, List[WorktreeInfo]] = {}
            for wt in organized_worktrees:
                if wt.type_category not in by_type:
                    by_type[wt.type_category] = []
                by_type[wt.type_category].append(wt)

            for wt_type, wt_list in by_type.items():
                lines.append(f"  {wt_type.upper()}:")
                for wt in wt_list:
                    wt_name: str = wt.path.split("/")[-1]
                    status_indicators: List[str] = []
                    if wt.has_uncommitted:
                        status_indicators.append("*modified*")
                    status_str: str = (
                        f" [{', '.join(status_indicators)}]"
                        if status_indicators
                        else ""
                    )
                    lines.append(
                        f"    {wt_name} ({wt.branch} @ {wt.commit}){status_str}"
                    )
        else:
            lines.append("  No active worktrees")
        lines.append("")

        # Branch Summary
        active_branches = [
            b
            for b in branches
            if b.name != "main" and (b.ahead > 0 or b.behind > 0 or b.has_worktree)
        ]
        lines.append(f"🌿 ACTIVE BRANCHES ({len(active_branches)})")
        lines.append("-" * 21)
        if active_branches:
            for branch in active_branches:
                indicators: List[str] = []
                if branch.ahead > 0:
                    indicators.append(f"+{branch.ahead}")
                if branch.behind > 0:
                    indicators.append(f"-{branch.behind}")
                if branch.has_worktree:
                    indicators.append("worktree")

                indicator_str: str = f" [{', '.join(indicators)}]" if indicators else ""
                lines.append(f"  {branch.name} @ {branch.commit}{indicator_str}")
        else:
            lines.append("  No active branches")
        lines.append("")

        # Summary
        lines.append("📊 SUMMARY")
        lines.append("-" * 10)
        lines.append(f"  • {len(issues)} open issues")
        lines.append(f"  • {len(prs)} open pull requests")
        lines.append(f"  • {len(organized_worktrees)} active worktrees")
        lines.append(f"  • {len(active_branches)} active branches")

        work_in_progress: int = len([wt for wt in worktrees if wt.has_uncommitted])
        if work_in_progress > 0:
            lines.append(
                f"  • ⚠️  {work_in_progress} worktrees with uncommitted changes"
            )

        return "\n".join(lines)

    def _format_json_report(
        self,
        issues: List[IssueInfo],
        prs: List[PRInfo],
        branches: List[BranchInfo],
        worktrees: List[WorktreeInfo],
    ) -> str:
        """Format as JSON report"""

        data: Dict[str, List[Dict[str, Any]]] = {
            "issues": [
                {
                    "number": issue.number,
                    "title": issue.title,
                    "state": issue.state,
                    "labels": issue.labels,
                    "assignee": issue.assignee,
                    "url": issue.url,
                }
                for issue in issues
            ],
            "pull_requests": [
                {
                    "number": pr.number,
                    "title": pr.title,
                    "state": pr.state,
                    "branch": pr.branch,
                    "base": pr.base,
                    "draft": pr.draft,
                    "url": pr.url,
                }
                for pr in prs
            ],
            "worktrees": [
                {
                    "path": wt.path,
                    "branch": wt.branch,
                    "commit": wt.commit,
                    "has_uncommitted": wt.has_uncommitted,
                    "type_category": wt.type_category,
                }
                for wt in worktrees
            ],
            "branches": [
                {
                    "name": branch.name,
                    "commit": branch.commit,
                    "ahead": branch.ahead,
                    "behind": branch.behind,
                    "last_commit_date": branch.last_commit_date,
                    "has_worktree": branch.has_worktree,
                    "worktree_path": branch.worktree_path,
                }
                for branch in branches
            ],
        }

        return json.dumps(data, indent=2)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Show comprehensive project status including issues, PRs, branches, and worktrees"
    )
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument(
        "--no-github",
        action="store_true",
        help="Skip GitHub API calls (issues and PRs)",
    )

    args = parser.parse_args()

    checker = ProjectStatusChecker()

    # Gather all status information
    issues = [] if args.no_github else checker.get_github_issues()
    prs = [] if args.no_github else checker.get_github_prs()
    branches = checker.get_local_branches()
    worktrees = checker.get_worktrees()

    # Format and output report
    format_type = "json" if args.json else "text"
    report = checker.format_status_report(issues, prs, branches, worktrees, format_type)

    print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
