"""
Structured logger with colored output for PR Guardian
Supports both human-readable colored output and JSON mode for CI environments
"""

import logging
import sys
import json
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        # Get color for log level
        color = self.COLORS.get(record.levelname, self.RESET)
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Format message
        level_colored = f"{color}{self.BOLD}{record.levelname:8}{self.RESET}"
        message = f"{timestamp} | {level_colored} | {record.name} | {record.getMessage()}"
        
        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in CI environments"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data)


def setup_logger(
    name: str,
    level: str = "INFO",
    json_mode: bool = False,
    log_file: Optional[str] = None
) -> logging.Logger:
    """
    Setup and configure logger
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_mode: Use JSON formatting instead of colored output
        log_file: Optional file path to write logs
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Set log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Choose formatter based on mode
    if json_mode:
        formatter = JSONFormatter()
    else:
        formatter = ColoredFormatter()
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JSONFormatter())  # Always use JSON for files
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Check if running in CI environment
def is_ci_environment() -> bool:
    """Check if running in CI environment"""
    ci_indicators = ['CI', 'CONTINUOUS_INTEGRATION', 'GITHUB_ACTIONS', 'GITLAB_CI']
    return any(indicator in sys.argv or indicator in str(sys.argv) for indicator in ci_indicators)


# Default logger setup
def configure_default_logger(level: str = "INFO") -> None:
    """
    Configure default logger for the application
    
    Args:
        level: Log level
    """
    json_mode = is_ci_environment()
    setup_logger('pr_guardian', level=level, json_mode=json_mode)


# Example usage logger
if __name__ == "__main__":
    # Test colored output
    logger = setup_logger(__name__, level="DEBUG")
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
    
    print("\n--- JSON Mode ---\n")
    
    # Test JSON output
    json_logger = setup_logger(__name__ + ".json", level="DEBUG", json_mode=True)
    
    json_logger.debug("This is a debug message")
    json_logger.info("This is an info message")
    json_logger.warning("This is a warning message")
    json_logger.error("This is an error message")
    json_logger.critical("This is a critical message")

# Made with Bob
