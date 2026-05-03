"""
Markdown formatters for MCP server responses
Converts analyzer output to clean, readable markdown
"""

from typing import Dict, List, Any


def format_full_report(metadata: Dict[str, Any], findings: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Format complete PR analysis report as markdown
    
    Args:
        metadata: PR metadata dictionary
        findings: Analysis findings with 4 categories
        
    Returns:
        Formatted markdown report
    """
    report = []
    
    # Header
    report.append("# 🛡️ PR Guardian Analysis Report\n")
    
    # PR Information
    report.append("## 📋 Pull Request Information\n")
    report.append(f"**Title:** {metadata.get('title', 'N/A')}\n")
    report.append(f"**Author:** {metadata.get('author', 'N/A')}\n")
    report.append(f"**Base Branch:** `{metadata.get('base_branch', 'N/A')}`\n")
    report.append(f"**Head Branch:** `{metadata.get('head_branch', 'N/A')}`\n")
    report.append(f"**Files Changed:** {len(metadata.get('changed_files', []))}\n")
    report.append(f"**Changes:** +{metadata.get('additions', 0)} / -{metadata.get('deletions', 0)}\n")
    
    # Summary
    total_issues = sum(len(findings.get(cat, [])) for cat in ['security', 'bugs', 'missing_tests', 'code_quality'])
    report.append(f"\n**Total Issues Found:** {total_issues}\n")
    
    # Security Findings
    report.append("\n## 🔒 Security Issues\n")
    security = findings.get('security', [])
    if security:
        for issue in security:
            severity_emoji = _get_severity_emoji(issue.get('severity', 'info'))
            report.append(f"\n### {severity_emoji} {issue.get('severity', 'info').upper()}\n")
            report.append(f"**Description:** {issue.get('description', 'N/A')}\n")
            if issue.get('suggestion'):
                report.append(f"**Suggestion:** {issue.get('suggestion')}\n")
            if issue.get('line'):
                report.append(f"**Line:** {issue.get('line')}\n")
    else:
        report.append("✅ No security issues detected\n")
    
    # Bug Findings
    report.append("\n## 🐛 Potential Bugs\n")
    bugs = findings.get('bugs', [])
    if bugs:
        for issue in bugs:
            severity_emoji = _get_severity_emoji(issue.get('severity', 'info'))
            report.append(f"\n### {severity_emoji} {issue.get('severity', 'info').upper()}\n")
            report.append(f"**Description:** {issue.get('description', 'N/A')}\n")
            if issue.get('suggestion'):
                report.append(f"**Suggestion:** {issue.get('suggestion')}\n")
            if issue.get('line'):
                report.append(f"**Line:** {issue.get('line')}\n")
    else:
        report.append("✅ No potential bugs detected\n")
    
    # Missing Tests
    report.append("\n## 🧪 Missing Tests\n")
    tests = findings.get('missing_tests', [])
    if tests:
        for issue in tests:
            severity_emoji = _get_severity_emoji(issue.get('severity', 'info'))
            report.append(f"\n### {severity_emoji} {issue.get('severity', 'info').upper()}\n")
            report.append(f"**Description:** {issue.get('description', 'N/A')}\n")
            if issue.get('suggestion'):
                report.append(f"**Suggestion:** {issue.get('suggestion')}\n")
            if issue.get('line'):
                report.append(f"**Line:** {issue.get('line')}\n")
    else:
        report.append("✅ Test coverage looks good\n")
    
    # Code Quality
    report.append("\n## 📊 Code Quality\n")
    quality = findings.get('code_quality', [])
    if quality:
        for issue in quality:
            severity_emoji = _get_severity_emoji(issue.get('severity', 'info'))
            report.append(f"\n### {severity_emoji} {issue.get('severity', 'info').upper()}\n")
            report.append(f"**Description:** {issue.get('description', 'N/A')}\n")
            if issue.get('suggestion'):
                report.append(f"**Suggestion:** {issue.get('suggestion')}\n")
            if issue.get('line'):
                report.append(f"**Line:** {issue.get('line')}\n")
    else:
        report.append("✅ Code quality looks good\n")
    
    return "".join(report)


def format_release_notes(metadata: Dict[str, Any], findings: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Format release notes from PR metadata
    
    Args:
        metadata: PR metadata dictionary
        findings: Analysis findings (used for breaking changes detection)
        
    Returns:
        Formatted release notes as markdown
    """
    notes = []
    
    # Header
    notes.append("# 📝 Release Notes\n")
    
    # PR Title as main change
    title = metadata.get('title', 'N/A')
    notes.append(f"\n## {title}\n")
    
    # Description
    description = metadata.get('description', '')
    if description:
        notes.append(f"\n{description}\n")
    
    # Changes Summary
    notes.append(f"\n### Changes\n")
    notes.append(f"- **Author:** {metadata.get('author', 'N/A')}\n")
    notes.append(f"- **Files Modified:** {len(metadata.get('changed_files', []))}\n")
    notes.append(f"- **Lines Changed:** +{metadata.get('additions', 0)} / -{metadata.get('deletions', 0)}\n")
    
    # Modified Files
    changed_files = metadata.get('changed_files', [])
    if changed_files:
        notes.append(f"\n### Modified Files\n")
        for file in changed_files[:10]:  # Limit to first 10
            notes.append(f"- `{file}`\n")
        if len(changed_files) > 10:
            notes.append(f"- ... and {len(changed_files) - 10} more files\n")
    
    # Breaking Changes (from security findings)
    security = findings.get('security', [])
    critical_issues = [s for s in security if s.get('severity') == 'critical']
    if critical_issues:
        notes.append(f"\n### ⚠️ Breaking Changes / Critical Issues\n")
        for issue in critical_issues:
            notes.append(f"- {issue.get('description', 'N/A')}\n")
    
    return "".join(notes)


def format_security_report(findings: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Format security-only report with CRITICAL and WARNING findings
    
    Args:
        findings: Analysis findings dictionary
        
    Returns:
        Formatted security report as markdown
    """
    report = []
    
    # Header
    report.append("# 🔒 Security Analysis Report\n")
    
    security = findings.get('security', [])
    
    # Filter for critical and warning only
    critical = [s for s in security if s.get('severity') == 'critical']
    warnings = [s for s in security if s.get('severity') == 'warning']
    
    # Summary
    report.append(f"\n**Critical Issues:** {len(critical)}\n")
    report.append(f"**Warnings:** {len(warnings)}\n")
    
    # Critical Issues
    if critical:
        report.append("\n## 🚨 Critical Security Issues\n")
        for i, issue in enumerate(critical, 1):
            report.append(f"\n### Issue {i}\n")
            report.append(f"**Description:** {issue.get('description', 'N/A')}\n")
            if issue.get('suggestion'):
                report.append(f"**Recommendation:** {issue.get('suggestion')}\n")
            if issue.get('line'):
                report.append(f"**Location:** Line {issue.get('line')}\n")
    else:
        report.append("\n✅ No critical security issues found\n")
    
    # Warnings
    if warnings:
        report.append("\n## ⚠️ Security Warnings\n")
        for i, issue in enumerate(warnings, 1):
            report.append(f"\n### Warning {i}\n")
            report.append(f"**Description:** {issue.get('description', 'N/A')}\n")
            if issue.get('suggestion'):
                report.append(f"**Recommendation:** {issue.get('suggestion')}\n")
            if issue.get('line'):
                report.append(f"**Location:** Line {issue.get('line')}\n")
    else:
        report.append("\n✅ No security warnings found\n")
    
    # Overall Assessment
    if not critical and not warnings:
        report.append("\n## ✅ Overall Assessment\n")
        report.append("No critical or warning-level security issues detected in this PR.\n")
    else:
        report.append("\n## 📋 Recommendations\n")
        report.append("Please review and address the security issues listed above before merging.\n")
    
    return "".join(report)


def _get_severity_emoji(severity: str) -> str:
    """Get emoji for severity level"""
    emoji_map = {
        'critical': '🚨',
        'warning': '⚠️',
        'info': 'ℹ️'
    }
    return emoji_map.get(severity.lower(), 'ℹ️')

# Made with Bob
