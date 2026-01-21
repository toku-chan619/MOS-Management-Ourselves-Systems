import logging
import sys
from typing import Any
import json
from datetime import datetime

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


class StructuredLogger:
    """Structured logger that outputs JSON-formatted logs for better parsing"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _format_message(self, level: str, message: str, **kwargs) -> str:
        """Format log message as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "logger": self.name,
            "message": message,
            **kwargs
        }
        return json.dumps(log_data, ensure_ascii=False)
    
    def info(self, message: str, **kwargs):
        self.logger.info(self._format_message("INFO", message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(self._format_message("WARNING", message, **kwargs))
    
    def error(self, message: str, **kwargs):
        self.logger.error(self._format_message("ERROR", message, **kwargs))
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(self._format_message("DEBUG", message, **kwargs))
    
    def exception(self, message: str, exc_info: Any = True, **kwargs):
        self.logger.exception(
            self._format_message("ERROR", message, **kwargs),
            exc_info=exc_info
        )


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)
