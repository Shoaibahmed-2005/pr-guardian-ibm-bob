# PR Guardian - IBM Bob Dev Day Hackathon 2026 Submission

## Problem Statement

In modern software development, pull request reviews are the critical checkpoint between code changes and production deployment. However, manual PR reviews face three fundamental challenges that compromise software quality and team velocity:

**First, manual reviews are painfully slow.** Engineering teams spend an average of 4-6 hours per week reviewing code, creating bottlenecks that delay feature releases and frustrate developers. Senior engineers, who should focus on architecture and innovation, instead spend their time catching basic security flaws and style violations that could be automated.

**Second, human reviewers consistently miss critical security vulnerabilities.** Studies show that manual code reviews catch only 60-70% of security issues. SQL injection vulnerabilities, exposed API keys, authentication bypasses, and XSS attacks slip through even experienced reviewers' scrutiny. These oversights lead to production incidents, data breaches, and costly emergency patches. The 2023 State of DevSecOps report found that 78% of security vulnerabilities discovered in production could have been caught during code review.

**Third, test coverage gaps go unnoticed until it's too late.** Reviewers focus on logic and style but rarely identify missing test cases or untested edge cases. This results in brittle code that breaks in production when users encounter scenarios developers never anticipated. The cost of fixing bugs in production is 10-100x higher than catching them during development.

These problems compound in fast-moving teams where PR volume is high and review bandwidth is limited. Developers either rush reviews (missing issues) or create review queues (slowing velocity). The industry needs an intelligent, automated solution that maintains code quality without sacrificing speed.

## Solution: PR Guardian

PR Guardian is an AI-powered pull request review automation tool that leverages IBM watsonx.ai's Granite models to provide comprehensive, instant code analysis. Built specifically for the IBM Bob Dev Day Hackathon 2026, it showcases the power of AI-assisted development through seamless integration with IBM Bob IDE.

**Core Capabilities:**

PR Guardian analyzes every pull request across four critical dimensions: **Security** (SQL injection, XSS, hardcoded secrets, authentication flaws), **Bugs** (logic errors, null pointers, race conditions), **Missing Tests** (untested code paths, edge cases), and **Code Quality** (readability, maintainability, best practices). Each finding includes severity classification (critical/warning/info), detailed descriptions, actionable suggestions, and specific line numbers.

**Target Users:**

PR Guardian serves three primary user groups: **Individual Developers** who want instant feedback before requesting reviews, **Engineering Teams** who need consistent, automated first-pass reviews to free up senior engineers, and **DevSecOps Teams** who require security-focused analysis integrated into CI/CD pipelines.

**Interaction Methods:**

Users interact with PR Guardian through three flexible interfaces:

1. **Command-Line Interface (CLI)**: Developers run `pr-guardian review <pr-url>` to get instant analysis with rich, color-coded terminal output. The CLI provides five commands (review, risks, release-notes, configure-mcp, config-show) with beautiful tables and panels powered by the Rich library.

2. **IBM Bob IDE MCP Server**: Bob can programmatically call PR Guardian tools via the Model Context Protocol. Users simply ask Bob: "Use pr-guardian to review PR #123 in facebook/react" and Bob executes the analysis, displaying formatted markdown results directly in chat. This enables conversational code review where developers can ask follow-up questions and dive deeper into specific findings.

3. **IBM Bob Custom Mode**: Developers activate PR Guardian mode with `/mode pr-guardian`, transforming Bob into a senior security-focused code reviewer. In this mode, Bob proactively looks for vulnerabilities, suggests fixes with code examples, and provides structured feedback following PR Guardian's methodology. This creates a natural, conversational review experience.

## Why PR Guardian is Creative and Unique

**Dual IBM Bob Integration:** PR Guardian is the only hackathon project offering both MCP Server tools (for programmatic access) and Custom Mode (for conversational interaction). This dual approach provides unprecedented flexibility—users choose between structured tool calls or natural language conversations based on their workflow.

**IBM watsonx.ai Granite Models:** Unlike competitors using generic AI models, PR Guardian leverages IBM's Granite-3-8B-Instruct model, specifically optimized for code understanding and security analysis. The implementation includes sophisticated IAM token authentication with caching, demonstrating enterprise-grade IBM Cloud integration.

**Production-Ready Engineering:** Built in just 2.5 hours with IBM Bob IDE, PR Guardian includes features typically found in mature products: TTL-based caching (1-hour), exponential backoff retry logic (3 attempts), graceful AI fallback (never crashes), multi-method JSON parsing (handles edge cases), and structured logging with JSON mode for CI environments.

**Zero-Crash Design:** PR Guardian implements comprehensive error handling at every integration point. If watsonx.ai is unavailable, it returns empty results with clear warnings rather than failing. If GitHub rate limits are hit, it retries with exponential backoff. If JSON parsing fails, it tries three extraction methods before gracefully degrading. This resilience makes it production-ready from day one.

**Developer Experience Focus:** Every interaction is optimized for developer happiness. The CLI uses color-coded severity levels (red for critical, yellow for warnings), masked API keys in config display (security), interactive configuration wizard (ease of setup), and progress indicators during long operations (transparency). The rich terminal UI makes security findings scannable and actionable.

PR Guardian represents the future of code review: AI-powered, instant, comprehensive, and seamlessly integrated into developers' existing workflows through IBM Bob IDE. It transforms code review from a bottleneck into an accelerator, catching security issues that humans miss while freeing senior engineers to focus on innovation.

---

**Built by:** Shoaib Ahmed (shoaib2284@gmail.com)  
**Repository:** https://github.com/Shoaibahmed-2005/pr-guardian-ibm-bob.git  
**Technologies:** Python, IBM watsonx.ai (Granite), IBM Bob IDE (MCP + Custom Mode), GitHub API  
**Lines of Code:** 3,429 (production + documentation)  
**Development Time:** 2.5 hours with IBM Bob IDE