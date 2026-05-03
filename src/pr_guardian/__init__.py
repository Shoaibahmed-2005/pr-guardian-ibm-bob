"""
PR Guardian - Automated PR Review with IBM Bob IDE Integration

A comprehensive tool for reviewing pull requests, detecting risks,
suggesting tests, and generating release notes.
"""

__version__ = "0.1.0"
__author__ = "PR Guardian Team"
__email__ = "contact@pr-guardian.dev"

from pr_guardian.ai.analyzer import PRAnalyzer
from pr_guardian.integrations.github_client import GitHubClient
from pr_guardian.config import Config

__all__ = [
    "PRAnalyzer",
    "GitHubClient",
    "Config",
    "__version__",
]

# Made with Bob
