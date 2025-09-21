import logging
import structlog
import sys
from typing import Any, Dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured logging for the application"""

    # Clear any existing handlers
    logging.root.handlers = []

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name)


# Health check utilities
class HealthChecker:
    def __init__(self):
        self.logger = get_logger("health_check")

    def check_openai_service(self, openai_service) -> Dict[str, Any]:
        """Check OpenAI service health"""
        try:
            # Simple test embedding
            test_result = openai_service.get_embedding("health check test")
            is_healthy = test_result is not None

            self.logger.info(
                "OpenAI health check completed",
                healthy=is_healthy,
                service="azure_openai",
            )

            return {
                "service": "azure_openai",
                "healthy": is_healthy,
                "response_time_ms": 0,  # Would measure in real implementation
            }
        except Exception as e:
            self.logger.error(
                "OpenAI health check failed", error=str(e), service="azure_openai"
            )
            return {"service": "azure_openai", "healthy": False, "error": str(e)}

    def check_search_service(self, search_service) -> Dict[str, Any]:
        """Check search service health"""
        try:
            stats = search_service.get_search_stats()
            is_healthy = stats is not None

            self.logger.info(
                "Search service health check completed",
                healthy=is_healthy,
                service="azure_search",
            )

            return {
                "service": "azure_search",
                "healthy": is_healthy,
                "document_count": stats.get("documentCount", 0) if stats else 0,
            }
        except Exception as e:
            self.logger.error(
                "Search service health check failed",
                error=str(e),
                service="azure_search",
            )
            return {"service": "azure_search", "healthy": False, "error": str(e)}
