"""
AI Analysis Engine for PR Guardian
Supports watsonx, OpenAI, and Anthropic for PR analysis
"""

import json
import re
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime, timedelta

from pr_guardian.utils.logger import get_logger

logger = get_logger(__name__)


class AIAnalyzerError(Exception):
    """Base exception for AI analyzer errors"""
    pass


class PRAnalyzer:
    """
    Core AI analysis engine for pull requests
    Supports multiple AI providers: watsonx (primary), OpenAI, Anthropic
    """
    
    def __init__(self, config: Any):
        """
        Initialize PR analyzer with configuration
        
        Args:
            config: Configuration object with AI settings
        """
        self.config = config
        self.provider = config.ai.provider.lower()
        self.api_key = config.ai.api_key
        self.model = config.ai.model
        self.api_url = config.ai.url
        
        # Watsonx IAM token cache
        self._iam_token: Optional[str] = None
        self._iam_token_expiry: Optional[datetime] = None
        
        logger.info(f"PR Analyzer initialized with provider: {self.provider}")
    
    def _get_iam_token(self) -> str:
        """
        Get IBM Cloud IAM token for watsonx authentication
        Caches token until expiry
        
        Returns:
            Bearer token string
            
        Raises:
            AIAnalyzerError: If token retrieval fails
        """
        # Return cached token if still valid
        if self._iam_token and self._iam_token_expiry:
            if datetime.now() < self._iam_token_expiry:
                return self._iam_token
        
        logger.info("Fetching new IAM token for watsonx")
        
        try:
            response = requests.post(
                "https://iam.cloud.ibm.com/identity/token",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                    "apikey": self.api_key
                },
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            self._iam_token = data["access_token"]
            
            # Token expires in 1 hour, cache for 50 minutes to be safe
            self._iam_token_expiry = datetime.now() + timedelta(minutes=50)
            
            logger.info("IAM token retrieved successfully")
            return self._iam_token
            
        except Exception as e:
            logger.error(f"Failed to get IAM token: {e}")
            raise AIAnalyzerError(f"Failed to authenticate with IBM Cloud: {e}")
    
    def _call_watsonx(self, prompt: str) -> str:
        """
        Call IBM watsonx.ai API
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            AI response text
        """
        token = self._get_iam_token()
        
        # Use granite model as specified
        model_id = self.model or "ibm/granite-3-8b-instruct"
        
        # Get project_id from config or environment
        project_id = None
        if hasattr(self.config.ai, 'project_id'):
            project_id = self.config.ai.project_id
        if not project_id:
            import os
            project_id = os.getenv('WATSONX_PROJECT_ID')
        
        # Watsonx endpoint - full URL with path
        base_url = self.api_url or "https://us-south.ml.cloud.ibm.com"
        # Ensure we have the full endpoint path
        if not base_url.endswith('/text/generation'):
            if not base_url.endswith('/ml/v1'):
                base_url = base_url.rstrip('/') + '/ml/v1/text/generation'
            else:
                base_url = base_url.rstrip('/') + '/text/generation'
        
        url = f"{base_url}?version=2023-05-29"
        
        payload = {
            "model_id": model_id,
            "input": prompt,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": 1000,
                "min_new_tokens": 1
            },
            "project_id": project_id
        }
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        logger.info(f"Calling watsonx at {url} with model: {model_id}")
        
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            result = data["results"][0]["generated_text"]
            
            logger.info(f"Watsonx response received: {len(result)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Watsonx API call failed: {e}")
            raise AIAnalyzerError(f"Watsonx API error: {e}")
    
    def _call_openai(self, prompt: str) -> str:
        """
        Call OpenAI API
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            AI response text
        """
        model = self.model or "gpt-4-turbo-preview"
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a code review expert. Analyze pull requests and provide structured feedback."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Calling OpenAI with model: {model}")
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            result = data["choices"][0]["message"]["content"]
            
            logger.info(f"OpenAI response received: {len(result)} characters")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            raise AIAnalyzerError(f"OpenAI API error: {e}")
    
    def _call_anthropic(self, prompt: str) -> str:
        """
        Call Anthropic API
        
        Args:
            prompt: Analysis prompt
            
        Returns:
            AI response text
        """
        model = self.model or "claude-3-sonnet-20240229"
        
        payload = {
            "model": model,
            "max_tokens": 2000,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Calling Anthropic with model: {model}")
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            data = response.json()
            result = data["content"][0]["text"]
            
            logger.info(f"Anthropic response received: {len(result)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Anthropic API call failed: {e}")
            raise AIAnalyzerError(f"Anthropic API error: {e}")
    
    def _build_analysis_prompt(self, diff: str, metadata: Dict[str, Any]) -> str:
        """
        Build analysis prompt for AI
        
        Args:
            diff: PR diff content
            metadata: PR metadata
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert code reviewer. Analyze this pull request and provide structured feedback.

PR Title: {metadata.get('title', 'N/A')}
Author: {metadata.get('author', 'N/A')}
Base Branch: {metadata.get('base_branch', 'N/A')}
Head Branch: {metadata.get('head_branch', 'N/A')}
Files Changed: {len(metadata.get('changed_files', []))}
Additions: +{metadata.get('additions', 0)}
Deletions: -{metadata.get('deletions', 0)}

Diff:
```
{diff[:8000]}
```

Analyze this PR and return your findings in EXACTLY this JSON structure (no markdown, no code fences, just pure JSON):

{{
  "security": [
    {{"severity": "critical|warning|info", "description": "...", "suggestion": "...", "line": 123}}
  ],
  "bugs": [
    {{"severity": "critical|warning|info", "description": "...", "suggestion": "...", "line": 123}}
  ],
  "missing_tests": [
    {{"severity": "critical|warning|info", "description": "...", "suggestion": "...", "line": 123}}
  ],
  "code_quality": [
    {{"severity": "critical|warning|info", "description": "...", "suggestion": "...", "line": 123}}
  ]
}}

Focus on:
- SECURITY: Vulnerabilities, exposed secrets, injection risks
- BUGS: Logic errors, null pointer issues, race conditions
- MISSING_TESTS: Untested code paths, missing edge cases
- CODE_QUALITY: Readability, maintainability, best practices

IMPORTANT: Return ONLY a single valid JSON object. No explanation, no markdown, no extra text before or after the JSON."""
        
        return prompt
    
    def _parse_ai_response(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse AI response and extract JSON
        
        Args:
            response: Raw AI response
            
        Returns:
            Parsed findings dictionary
        """
        # Strip markdown code fences if present
        cleaned = response.strip()
        
        # Remove ```json and ``` markers
        if cleaned.startswith("```"):
            # Find the first newline after ```
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline + 1:]
            # Remove trailing ```
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        
        cleaned = cleaned.strip()
        
        # Try multiple extraction methods
        json_text = None
        
        # Method 1: Try direct parsing
        try:
            findings = json.loads(cleaned)
            logger.info(f"Parsed findings: {sum(len(v) for v in findings.values())} total issues")
            
            # Validate structure
            required_keys = ["security", "bugs", "missing_tests", "code_quality"]
            for key in required_keys:
                if key not in findings:
                    findings[key] = []
            
            return findings
        except json.JSONDecodeError:
            logger.debug("Direct JSON parsing failed, trying extraction methods")
        
        # Method 2: Extract first JSON object using regex
        try:
            import re
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                json_text = match.group(0)
                findings = json.loads(json_text)
                logger.info(f"Parsed findings using regex: {sum(len(v) for v in findings.values())} total issues")
                
                # Validate structure
                required_keys = ["security", "bugs", "missing_tests", "code_quality"]
                for key in required_keys:
                    if key not in findings:
                        findings[key] = []
                
                return findings
        except (json.JSONDecodeError, AttributeError):
            logger.debug("Regex extraction failed")
        
        # Method 3: Extract between first { and last }
        try:
            if '{' in cleaned and '}' in cleaned:
                start = cleaned.index('{')
                end = cleaned.rindex('}') + 1
                json_text = cleaned[start:end]
                findings = json.loads(json_text)
                logger.info(f"Parsed findings using bracket extraction: {sum(len(v) for v in findings.values())} total issues")
                
                # Validate structure
                required_keys = ["security", "bugs", "missing_tests", "code_quality"]
                for key in required_keys:
                    if key not in findings:
                        findings[key] = []
                
                return findings
        except (json.JSONDecodeError, ValueError):
            logger.debug("Bracket extraction failed")
        
        # All methods failed
        logger.error(f"Failed to parse AI response as JSON after all attempts")
        logger.debug(f"Response was: {cleaned[:500]}")
        raise AIAnalyzerError(f"AI returned invalid JSON. Could not extract valid JSON object from response.")
    
    def analyze(self, diff: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze PR diff using AI
        
        Args:
            diff: PR diff content
            metadata: PR metadata dictionary
            
        Returns:
            Analysis results with findings in 4 categories
        """
        logger.info("Starting PR analysis")
        
        try:
            # Build prompt
            prompt = self._build_analysis_prompt(diff, metadata)
            
            # Call appropriate AI provider
            if self.provider == "watsonx":
                response = self._call_watsonx(prompt)
            elif self.provider == "openai":
                response = self._call_openai(prompt)
            elif self.provider == "anthropic":
                response = self._call_anthropic(prompt)
            else:
                raise AIAnalyzerError(f"Unsupported AI provider: {self.provider}")
            
            # Parse response
            findings = self._parse_ai_response(response)
            
            return {
                "success": True,
                "provider": self.provider,
                "findings": findings,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            
            # Return graceful fallback
            return {
                "success": False,
                "error": str(e),
                "warning": "AI analysis unavailable, returning empty results",
                "provider": self.provider,
                "findings": {
                    "security": [],
                    "bugs": [],
                    "missing_tests": [],
                    "code_quality": []
                },
                "metadata": metadata
            }

# Made with Bob
