"""
PR Guardian CLI
Command-line interface using Click and Rich
"""

from dotenv import load_dotenv
load_dotenv()

import json
import sys
from pathlib import Path
from typing import Dict, Any

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from pr_guardian import __version__
from pr_guardian.config import load_config, Config
from pr_guardian.integrations.github_client import GitHubClient, GitHubClientError
from pr_guardian.ai.analyzer import PRAnalyzer, AIAnalyzerError
from pr_guardian.utils.logger import setup_logger

console = Console()
logger = setup_logger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="PR Guardian")
def cli():
    """
    🛡️ PR Guardian - Automated PR Review with IBM Bob IDE Integration
    
    Review pull requests, detect risks, suggest tests, and generate release notes.
    """
    pass


@cli.command()
@click.argument("pr_url")
def review(pr_url: str):
    """
    Run full PR analysis and display results in a rich table.
    
    Example: pr-guardian review https://github.com/owner/repo/pull/123
    """
    try:
        console.print("\n[bold blue]🔍 Analyzing PR...[/bold blue]\n")
        
        # Load config and initialize clients
        config = load_config()
        github_client = GitHubClient(config=config)
        analyzer = PRAnalyzer(config=config)
        
        # Fetch PR data
        with console.status("[bold green]Fetching PR data..."):
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
        
        # Display PR summary
        summary_text = f"""[bold]Title:[/bold] {metadata.title}
[bold]Author:[/bold] {metadata.author}
[bold]Base Branch:[/bold] {metadata.base_branch}
[bold]Head Branch:[/bold] {metadata.head_branch}
[bold]Files Changed:[/bold] {len(metadata.changed_files)}
[bold]Changes:[/bold] +{metadata.additions} / -{metadata.deletions}"""
        
        summary_panel = Panel(
            summary_text,
            title="📋 Pull Request Summary",
            border_style="blue"
        )
        console.print(summary_panel)
        console.print()
        
        # Run AI analysis
        with console.status("[bold green]Running AI analysis..."):
            analysis_result = analyzer.analyze(diff, metadata_dict)
        
        if not analysis_result.get('success', False):
            console.print(f"[bold red]⚠️  Analysis Warning:[/bold red] {analysis_result.get('error', 'Unknown error')}")
            return
        
        # Display findings in table
        findings = analysis_result.get('findings', {})
        
        # Create table
        table = Table(title="🛡️ Analysis Results", show_header=True, header_style="bold")
        table.add_column("Category", style="cyan", width=15)
        table.add_column("Severity", width=10)
        table.add_column("Description", width=50)
        table.add_column("Suggestion", width=40)
        
        # Add rows for each category
        total_issues = 0
        for category in ['security', 'bugs', 'missing_tests', 'code_quality']:
            category_findings = findings.get(category, [])
            total_issues += len(category_findings)
            
            for finding in category_findings:
                severity = finding.get('severity', 'info')
                
                # Color-code severity
                if severity == 'critical':
                    severity_text = f"[bold red]{severity.upper()}[/bold red]"
                    row_style = "red"
                elif severity == 'warning':
                    severity_text = f"[bold yellow]{severity.upper()}[/bold yellow]"
                    row_style = "yellow"
                else:
                    severity_text = f"[bold blue]{severity.upper()}[/bold blue]"
                    row_style = "blue"
                
                table.add_row(
                    category.replace('_', ' ').title(),
                    severity_text,
                    finding.get('description', 'N/A'),
                    finding.get('suggestion', 'N/A'),
                    style=row_style
                )
        
        console.print(table)
        console.print()
        
        # Summary
        if total_issues == 0:
            console.print("[bold green]✅ No issues found! PR looks good.[/bold green]\n")
        else:
            console.print(f"[bold]Total Issues Found:[/bold] {total_issues}\n")
        
    except GitHubClientError as e:
        console.print(f"[bold red]❌ GitHub Error:[/bold red] {e}")
        sys.exit(1)
    except AIAnalyzerError as e:
        console.print(f"[bold red]❌ AI Analysis Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("pr_url")
def risks(pr_url: str):
    """
    Display security findings only.
    
    Example: pr-guardian risks https://github.com/owner/repo/pull/123
    """
    try:
        console.print("\n[bold red]🔒 Analyzing Security Risks...[/bold red]\n")
        
        # Load config and initialize clients
        config = load_config()
        github_client = GitHubClient(config=config)
        analyzer = PRAnalyzer(config=config)
        
        # Fetch PR data
        with console.status("[bold green]Fetching PR data..."):
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
        with console.status("[bold green]Running security analysis..."):
            analysis_result = analyzer.analyze(diff, metadata_dict)
        
        if not analysis_result.get('success', False):
            console.print(f"[bold red]⚠️  Analysis Warning:[/bold red] {analysis_result.get('error', 'Unknown error')}")
            return
        
        # Get security findings
        findings = analysis_result.get('findings', {})
        security_findings = findings.get('security', [])
        
        # Build report text
        if not security_findings:
            report_text = "[bold green]✅ No security issues detected![/bold green]"
        else:
            report_lines = []
            for i, finding in enumerate(security_findings, 1):
                severity = finding.get('severity', 'info')
                
                # Severity emoji
                if severity == 'critical':
                    emoji = "🔴"
                elif severity == 'warning':
                    emoji = "🟡"
                else:
                    emoji = "🔵"
                
                report_lines.append(f"\n{emoji} [bold]{severity.upper()}[/bold]")
                report_lines.append(f"[bold]Description:[/bold] {finding.get('description', 'N/A')}")
                if finding.get('suggestion'):
                    report_lines.append(f"[bold]Suggestion:[/bold] {finding.get('suggestion')}")
                if finding.get('line'):
                    report_lines.append(f"[bold]Line:[/bold] {finding.get('line')}")
            
            report_text = "\n".join(report_lines)
        
        # Display in panel
        panel = Panel(
            report_text,
            title="🔒 Security Risk Report",
            border_style="red",
            padding=(1, 2)
        )
        console.print(panel)
        console.print()
        
    except GitHubClientError as e:
        console.print(f"[bold red]❌ GitHub Error:[/bold red] {e}")
        sys.exit(1)
    except AIAnalyzerError as e:
        console.print(f"[bold red]❌ AI Analysis Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("pr_url")
def release_notes(pr_url: str):
    """
    Generate and display release notes.
    
    Example: pr-guardian release-notes https://github.com/owner/repo/pull/123
    """
    try:
        console.print("\n[bold green]📝 Generating Release Notes...[/bold green]\n")
        
        # Load config and initialize clients
        config = load_config()
        github_client = GitHubClient(config=config)
        
        # Fetch PR data
        with console.status("[bold green]Fetching PR data..."):
            metadata, diff = github_client.get_pr_from_url(pr_url)
        
        # Build release notes
        notes_lines = []
        notes_lines.append(f"[bold]{metadata.title}[/bold]\n")
        
        if metadata.description:
            notes_lines.append(f"{metadata.description}\n")
        
        notes_lines.append(f"[bold]Author:[/bold] {metadata.author}")
        notes_lines.append(f"[bold]Files Modified:[/bold] {len(metadata.changed_files)}")
        notes_lines.append(f"[bold]Changes:[/bold] +{metadata.additions} / -{metadata.deletions}\n")
        
        # List changed files (first 10)
        if metadata.changed_files:
            notes_lines.append("[bold]Modified Files:[/bold]")
            for file in metadata.changed_files[:10]:
                notes_lines.append(f"  • {file}")
            if len(metadata.changed_files) > 10:
                notes_lines.append(f"  • ... and {len(metadata.changed_files) - 10} more files")
        
        notes_text = "\n".join(notes_lines)
        
        # Display in panel
        panel = Panel(
            notes_text,
            title="📝 Release Notes",
            border_style="green",
            padding=(1, 2)
        )
        console.print(panel)
        console.print()
        
    except GitHubClientError as e:
        console.print(f"[bold red]❌ GitHub Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
def configure_mcp():
    """
    Interactive configuration for MCP server.
    Prompts for credentials and updates mcp_config.json.
    
    Example: pr-guardian configure-mcp
    """
    try:
        console.print("\n[bold blue]⚙️  MCP Server Configuration[/bold blue]\n")
        console.print("Please provide your credentials:\n")
        
        # Prompt for credentials
        github_token = Prompt.ask("GitHub Token", password=True)
        watsonx_api_key = Prompt.ask("Watsonx API Key", password=True)
        watsonx_project_id = Prompt.ask("Watsonx Project ID")
        
        # Load existing config or create new
        config_path = Path("mcp_config.json")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        else:
            config_data = {"mcpServers": {}}
        
        # Update config
        config_data["mcpServers"]["pr-guardian"] = {
            "command": "python",
            "args": ["-m", "mcp_server.server"],
            "env": {
                "GITHUB_TOKEN": github_token,
                "WATSONX_API_KEY": watsonx_api_key,
                "WATSONX_PROJECT_ID": watsonx_project_id,
                "AI_PROVIDER": "watsonx"
            },
            "description": "PR Guardian - Automated PR review with security analysis"
        }
        
        # Write config
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        console.print(f"\n[bold green]✅ Configuration saved to {config_path}[/bold green]")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("1. Copy the contents of mcp_config.json")
        console.print("2. Paste into Bob IDE MCP settings")
        console.print("3. Restart Bob IDE\n")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)


@cli.command()
def config_show():
    """
    Display current configuration.
    
    Example: pr-guardian config-show
    """
    try:
        console.print("\n[bold blue]⚙️  Current Configuration[/bold blue]\n")
        
        # Load config
        config = load_config()
        
        # Create table
        table = Table(title="Configuration", show_header=True, header_style="bold cyan")
        table.add_column("Setting", style="cyan", width=30)
        table.add_column("Value", width=50)
        
        # GitHub settings
        github_token = config.github.token or "Not set"
        if github_token != "Not set" and len(github_token) > 4:
            github_token = f"...{github_token[-4:]}"
        
        table.add_row("GitHub Token", github_token)
        table.add_row("GitHub API URL", config.github.api_url)
        
        # AI settings
        table.add_row("AI Provider", config.ai.provider)
        
        ai_key = config.ai.api_key or "Not set"
        if ai_key != "Not set" and len(ai_key) > 4:
            ai_key = f"...{ai_key[-4:]}"
        
        table.add_row("AI API Key", ai_key)
        table.add_row("AI Model", config.ai.model or "Default")
        
        if config.ai.url:
            table.add_row("AI URL", config.ai.url)
        
        # App settings
        table.add_row("Log Level", config.app.log_level)
        table.add_row("Cache Enabled", str(config.app.cache_enabled))
        
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        sys.exit(1)


def main():
    """Main entry point for CLI"""
    cli()


if __name__ == "__main__":
    main()

# Made with Bob
