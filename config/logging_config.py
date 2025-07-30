"""
Logging configuration for the application.
"""

import logging
import logging.config
import json
import sys
from datetime import datetime
from typing import Dict, Any
from config.settings import get_settings

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ("name", "msg", "args", "levelname", "levelno", "pathname", 
                          "filename", "module", "lineno", "funcName", "created", 
                          "msecs", "relativeCreated", "thread", "threadName", 
                          "processName", "process", "getMessage", "exc_info", 
                          "exc_text", "stack_info"):
                log_entry[key] = value
        
        return json.dumps(log_entry)

def setup_logging() -> None:
    """Setup application logging configuration."""
    settings = get_settings()
    
    # Configure logging based on format preference
    if settings.LOG_FORMAT.lower() == "json":
        formatter_class = JSONFormatter
        format_string = ""
    else:
        formatter_class = logging.Formatter
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": formatter_class,
                "format": format_string
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": sys.stdout
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "default",
                "filename": settings.LOG_FILE,
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": settings.LOG_LEVEL,
                "handlers": ["console", "file"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
