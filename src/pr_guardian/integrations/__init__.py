"""
Integrations module for PR Guardian
Exports GitHub client and other external integrations
"""

from pr_guardian.integrations.github_client import (
    GitHubClient,
    GitHubClientError,
    AuthenticationError,
    InvalidPRURLError,
    RateLimitError,
    PRMetadata,
)

__all__ = [
    "GitHubClient",
    "GitHubClientError",
    "AuthenticationError",
    "InvalidPRURLError",
    "RateLimitError",
    "PRMetadata",
]

# Made with Bob
