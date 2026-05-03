"""
MCP Server for PR Guardian
Exposes PR analysis tools via Model Context Protocol
"""

from dotenv import load_dotenv
load_dotenv()

import asyncio
import sys
from typing import Any, Sequence

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

from pr_guardian.config import load_config
from pr_guardian.integrations.github_client import GitHubClient, GitHubClientError
from pr_guardian.ai.analyzer import PRAnalyzer, AIAnalyzerError
from pr_guardian.utils.logger import setup_logger
from mcp_server.formatters import format_full_report, format_release_notes, format_security_report

# Setup logging (JSON mode for MCP to avoid stdout pollution)
logger = setup_logger(__name__, json_mode=True)

# Initialize server
app = Server("pr-guardian")

# Global config
config = None


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="review_pr",
            description="Run full PR Guardian analysis on a GitHub pull request. Returns comprehensive report with security, bugs, missing tests, and code quality findings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pr_url": {
                        "type": "string",
                        "description": "GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)"
                    }
                },
                "required": ["pr_url"]
            }
        ),
        Tool(
            name="get_release_notes",
            description="Generate release notes from a GitHub pull request. Returns formatted markdown suitable for changelogs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pr_url": {
                        "type": "string",
                        "description": "GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)"
                    }
                },
                "required": ["pr_url"]
            }
        ),
        Tool(
            name="check_security",
            description="Run security-focused analysis on a GitHub pull request. Returns only CRITICAL and WARNING security findings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pr_url": {
                        "type": "string",
                        "description": "GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)"
                    }
                },
                "required": ["pr_url"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    """Handle tool calls"""
    global config
    
    # Load config if not already loaded
    if config is None:
        config = load_config()
    
    try:
        if name == "review_pr":
            result = await review_pr(arguments["pr_url"])
        elif name == "get_release_notes":
            result = await get_release_notes(arguments["pr_url"])
        elif name == "check_security":
            result = await check_security(arguments["pr_url"])
        else:
            result = f"Error: Unknown tool '{name}'"
        
        return [TextContent(type="text", text=result)]
        
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        error_msg = f"# ❌ Error\n\nFailed to execute {name}: {str(e)}\n\nPlease check your configuration and try again."
        return [TextContent(type="text", text=error_msg)]


async def review_pr(pr_url: str) -> str:
    """
    Run full PR Guardian analysis
    
    Args:
        pr_url: GitHub PR URL
        
    Returns:
        Formatted markdown report
    """
    try:
        logger.info(f"Starting full PR review: {pr_url}")
        
        # Initialize clients
        github_client = GitHubClient(config=config)
        analyzer = PRAnalyzer(config=config)
        
        # Fetch PR data
        logger.info("Fetching PR data from GitHub")
        metadata, diff = github_client.get_pr_from_url(pr_url)
        
        # Convert metadata to dict
        metadata_dict = {
            'title': metadata.title,
            'description': metadata.description,
            'author': metadata.author,
            'base_branch': metadata.base_branch,
            'head_branch': metadata.head_branch,
            'changed_files': metadata.changed_files,
            'additions': metadata.additions,
            'deletions': metadata.deletions
        }
        
        # Run AI analysis
        logger.info("Running AI analysis")
        analysis_result = analyzer.analyze(diff, metadata_dict)
        
        # Check if analysis was successful
        if not analysis_result.get('success', False):
            error_msg = analysis_result.get('error', 'Unknown error')
            return f"# ⚠️ Analysis Warning\n\nAI analysis encountered an issue: {error_msg}\n\nPlease check your AI provider configuration."
        
        # Format report
        findings = analysis_result.get('findings', {})
        report = format_full_report(metadata_dict, findings)
        
        logger.info("PR review completed successfully")
        return report
        
    except GitHubClientError as e:
        logger.error(f"GitHub error: {e}")
        return f"# ❌ GitHub Error\n\n{str(e)}\n\nPlease check:\n- Your GITHUB_TOKEN is valid\n- The PR URL is correct\n- You have access to the repository"
        
    except AIAnalyzerError as e:
        logger.error(f"AI analyzer error: {e}")
        return f"# ❌ AI Analysis Error\n\n{str(e)}\n\nPlease check:\n- Your AI provider credentials are correct\n- The AI service is available\n- Your API quota is not exceeded"
        
    except Exception as e:
        logger.error(f"Unexpected error in review_pr: {e}")
        return f"# ❌ Unexpected Error\n\n{str(e)}\n\nPlease report this issue if it persists."


async def get_release_notes(pr_url: str) -> str:
    """
    Generate release notes from PR
    
    Args:
        pr_url: GitHub PR URL
        
    Returns:
        Formatted release notes as markdown
    """
    try:
        logger.info(f"Generating release notes: {pr_url}")
        
        # Initialize clients
        github_client = GitHubClient(config=config)
        analyzer = PRAnalyzer(config=config)
        
        # Fetch PR data
        logger.info("Fetching PR data from GitHub")
        metadata, diff = github_client.get_pr_from_url(pr_url)
        
        # Convert metadata to dict
        metadata_dict = {
            'title': metadata.title,
            'description': metadata.description,
            'author': metadata.author,
            'base_branch': metadata.base_branch,
            'head_branch': metadata.head_branch,
            'changed_files': metadata.changed_files,
            'additions': metadata.additions,
            'deletions': metadata.deletions
        }
        
        # Run AI analysis (to detect breaking changes)
        logger.info("Running AI analysis")
        analysis_result = analyzer.analyze(diff, metadata_dict)
        
        # Format release notes
        findings = analysis_result.get('findings', {})
        notes = format_release_notes(metadata_dict, findings)
        
        logger.info("Release notes generated successfully")
        return notes
        
    except GitHubClientError as e:
        logger.error(f"GitHub error: {e}")
        return f"# ❌ GitHub Error\n\n{str(e)}\n\nPlease check your GITHUB_TOKEN and PR URL."
        
    except Exception as e:
        logger.error(f"Unexpected error in get_release_notes: {e}")
        return f"# ❌ Error\n\n{str(e)}"


async def check_security(pr_url: str) -> str:
    """
    Run security-focused analysis
    
    Args:
        pr_url: GitHub PR URL
        
    Returns:
        Security report with CRITICAL and WARNING findings
    """
    try:
        logger.info(f"Running security check: {pr_url}")
        
        # Initialize clients
        github_client = GitHubClient(config=config)
        analyzer = PRAnalyzer(config=config)
        
        # Fetch PR data
        logger.info("Fetching PR data from GitHub")
        metadata, diff = github_client.get_pr_from_url(pr_url)
        
        # Convert metadata to dict
        metadata_dict = {
            'title': metadata.title,
            'description': metadata.description,
            'author': metadata.author,
            'base_branch': metadata.base_branch,
            'head_branch': metadata.head_branch,
            'changed_files': metadata.changed_files,
            'additions': metadata.additions,
            'deletions': metadata.deletions
        }
        
        # Run AI analysis
        logger.info("Running security analysis")
        analysis_result = analyzer.analyze(diff, metadata_dict)
        
        # Check if analysis was successful
        if not analysis_result.get('success', False):
            error_msg = analysis_result.get('error', 'Unknown error')
            return f"# ⚠️ Analysis Warning\n\nSecurity analysis encountered an issue: {error_msg}"
        
        # Format security report
        findings = analysis_result.get('findings', {})
        report = format_security_report(findings)
        
        logger.info("Security check completed successfully")
        return report
        
    except GitHubClientError as e:
        logger.error(f"GitHub error: {e}")
        return f"# ❌ GitHub Error\n\n{str(e)}"
        
    except AIAnalyzerError as e:
        logger.error(f"AI analyzer error: {e}")
        return f"# ❌ AI Analysis Error\n\n{str(e)}"
        
    except Exception as e:
        logger.error(f"Unexpected error in check_security: {e}")
        return f"# ❌ Error\n\n{str(e)}"


async def main():
    """Main entry point for MCP server"""
    logger.info("Starting PR Guardian MCP server")
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
