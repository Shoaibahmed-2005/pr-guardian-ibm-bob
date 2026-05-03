"""
GitHub API Client for PR Guardian
Handles authentication, PR data fetching, and rate limiting
"""

import os
import re
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import requests
from cachetools import TTLCache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from pr_guardian.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PRMetadata:
    """Pull request metadata"""
    title: str
    description: str
    author: str
    base_branch: str
    head_branch: str
    changed_files: List[str]
    additions: int
    deletions: int


class GitHubClientError(Exception):
    """Base exception for GitHub client errors"""
    pass


class AuthenticationError(GitHubClientError):
    """Raised when authentication fails"""
    pass


class InvalidPRURLError(GitHubClientError):
    """Raised when PR URL is invalid"""
    pass


class RateLimitError(GitHubClientError):
    """Raised when rate limit is exceeded"""
    pass


class GitHubClient:
    """
    GitHub API client with caching and rate limiting
    Uses requests library without external GitHub SDK
    """
    
    def __init__(self, token: Optional[str] = None, config: Optional[Any] = None):
        """
        Initialize GitHub client
        
        Args:
            token: GitHub personal access token
            config: Configuration object (optional)
            
        Raises:
            AuthenticationError: If no token is provided
        """
        # Get token from parameter, config, or environment
        self.token = token
        if not self.token and config:
            self.token = config.github.token
        if not self.token:
            self.token = os.getenv("GITHUB_TOKEN")
        
        if not self.token:
            raise AuthenticationError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable "
                "or provide token in config file (~/.pr-guardian/config.yaml)"
            )
        
        self.api_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PR-Guardian/0.1.0"
        })
        
        # Cache with 1 hour TTL
        self.cache = TTLCache(maxsize=100, ttl=3600)
        
        logger.info("GitHub client initialized")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError)
    )
    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make HTTP request with retry logic and rate limit handling
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            Response object
            
        Raises:
            RateLimitError: If rate limit is exceeded
            GitHubClientError: For other API errors
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        logger.debug(f"Making {method} request to {url}")
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Check rate limit
            remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            if remaining < 100:
                logger.warning(f"GitHub API rate limit low: {remaining} requests remaining")
            
            # Handle rate limit exceeded
            if response.status_code == 403 and remaining == 0:
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                wait_time = reset_time - int(time.time())
                raise RateLimitError(
                    f"GitHub API rate limit exceeded. Resets in {wait_time} seconds"
                )
            
            # Handle authentication errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid GitHub token")
            
            # Raise for other HTTP errors
            response.raise_for_status()
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise GitHubClientError(f"GitHub API request failed: {e}")
    
    def parse_pr_url(self, url: str) -> Tuple[str, str, int]:
        """
        Parse GitHub PR URL to extract owner, repo, and PR number
        
        Args:
            url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            
        Returns:
            Tuple of (owner, repo, pr_number)
            
        Raises:
            InvalidPRURLError: If URL format is invalid
        """
        # Pattern: https://github.com/owner/repo/pull/123
        pattern = r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, url.rstrip("/"))
        
        if not match:
            raise InvalidPRURLError(
                f"Invalid GitHub PR URL: {url}\n"
                "Expected format: https://github.com/owner/repo/pull/123"
            )
        
        owner, repo, pr_number = match.groups()
        return owner, repo, int(pr_number)
    
    def get_pr_metadata(self, owner: str, repo: str, pr_number: int) -> PRMetadata:
        """
        Fetch pull request metadata
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            
        Returns:
            PRMetadata object with PR information
        """
        cache_key = f"metadata:{owner}/{repo}/{pr_number}"
        
        # Check cache
        if cache_key in self.cache:
            logger.debug(f"Returning cached metadata for {cache_key}")
            return self.cache[cache_key]
        
        logger.info(f"Fetching PR metadata: {owner}/{repo}#{pr_number}")
        
        # Fetch PR data
        endpoint = f"repos/{owner}/{repo}/pulls/{pr_number}"
        response = self._make_request("GET", endpoint)
        data = response.json()
        
        # Fetch files
        files_endpoint = f"repos/{owner}/{repo}/pulls/{pr_number}/files"
        files_response = self._make_request("GET", files_endpoint)
        files_data = files_response.json()
        
        # Extract changed files
        changed_files = [file["filename"] for file in files_data]
        
        # Create metadata object
        metadata = PRMetadata(
            title=data["title"],
            description=data["body"] or "",
            author=data["user"]["login"],
            base_branch=data["base"]["ref"],
            head_branch=data["head"]["ref"],
            changed_files=changed_files,
            additions=data["additions"],
            deletions=data["deletions"]
        )
        
        # Cache the result
        self.cache[cache_key] = metadata
        
        logger.info(f"Fetched metadata: {len(changed_files)} files, +{metadata.additions}/-{metadata.deletions}")
        
        return metadata
    
    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """
        Fetch pull request diff in unified format
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            
        Returns:
            Raw unified diff string
        """
        cache_key = f"diff:{owner}/{repo}/{pr_number}"
        
        # Check cache
        if cache_key in self.cache:
            logger.debug(f"Returning cached diff for {cache_key}")
            return self.cache[cache_key]
        
        logger.info(f"Fetching PR diff: {owner}/{repo}#{pr_number}")
        
        # Request diff format
        endpoint = f"repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {"Accept": "application/vnd.github.v3.diff"}
        
        response = self._make_request("GET", endpoint, headers=headers)
        diff = response.text
        
        # Cache the result
        self.cache[cache_key] = diff
        
        logger.info(f"Fetched diff: {len(diff)} characters")
        
        return diff
    
    def get_pr_from_url(self, pr_url: str) -> Tuple[PRMetadata, str]:
        """
        Convenience method to fetch both metadata and diff from PR URL
        
        Args:
            pr_url: GitHub PR URL
            
        Returns:
            Tuple of (PRMetadata, diff_string)
        """
        owner, repo, pr_number = self.parse_pr_url(pr_url)
        metadata = self.get_pr_metadata(owner, repo, pr_number)
        diff = self.get_pr_diff(owner, repo, pr_number)
        return metadata, diff
    
    def clear_cache(self) -> None:
        """Clear the cache"""
        self.cache.clear()
        logger.info("Cache cleared")
    
    def close(self) -> None:
        """Close the session"""
        self.session.close()
        logger.info("GitHub client closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Example usage
if __name__ == "__main__":
    # Test the client
    try:
        client = GitHubClient()
        
        # Test URL parsing
        url = "https://github.com/octocat/Hello-World/pull/1"
        owner, repo, pr_num = client.parse_pr_url(url)
        print(f"Parsed: {owner}/{repo}#{pr_num}")
        
        # Test metadata fetching
        metadata = client.get_pr_metadata(owner, repo, pr_num)
        print(f"\nTitle: {metadata.title}")
        print(f"Author: {metadata.author}")
        print(f"Files: {len(metadata.changed_files)}")
        print(f"Changes: +{metadata.additions}/-{metadata.deletions}")
        
        # Test diff fetching
        diff = client.get_pr_diff(owner, repo, pr_num)
        print(f"\nDiff length: {len(diff)} characters")
        
    except GitHubClientError as e:
        print(f"Error: {e}")

# Made with Bob
