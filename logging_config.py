import logging
import structlog
import sys
import os
from typing import Any, Dict
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure import metrics_exporter
from opencensus.stats import aggregation as aggregation_module
from opencensus.stats import measure as measure_module
from opencensus.stats import stats as stats_module
from opencensus.stats import view as view_module
from opencensus.tags import tag_map as tag_map_module


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured logging with Application Insights integration"""

    # Clear any existing handlers
    logging.root.handlers = []

    # Get Application Insights connection string
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

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
    handlers = [logging.StreamHandler(sys.stdout)]

    # Add Azure handler if connection string is available
    if connection_string:
        azure_handler = AzureLogHandler(connection_string=connection_string)
        handlers.append(azure_handler)

    logging.basicConfig(
        format="%(message)s",
        handlers=handlers,
        level=getattr(logging, log_level.upper()),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name)


# Application Insights metrics
class AppInsightsMetrics:
    def __init__(self):
        self.connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        if self.connection_string:
            self.exporter = metrics_exporter.new_metrics_exporter(
                connection_string=self.connection_string
            )
            self.stats = stats_module.stats
            self.view_manager = self.stats.view_manager

            # Define custom metrics
            self.request_duration = measure_module.MeasureFloat(
                "rag_request_duration", "Duration of RAG requests", "ms"
            )
            self.embedding_duration = measure_module.MeasureFloat(
                "embedding_duration", "Duration of embedding generation", "ms"
            )
            self.search_duration = measure_module.MeasureFloat(
                "search_duration", "Duration of search operations", "ms"
            )

            # Create views
            self._create_views()

    def _create_views(self):
        if not self.connection_string:
            return

        request_duration_view = view_module.View(
            "rag_request_duration_view",
            "The distribution of RAG request durations",
            [],
            self.request_duration,
            aggregation_module.DistributionAggregation(
                [50.0, 100.0, 200.0, 400.0, 1000.0, 2000.0, 5000.0]
            ),
        )

        self.view_manager.register_view(request_duration_view)
        self.view_manager.register_exporter(self.exporter)

    def record_request_duration(self, duration_ms: float):
        if self.connection_string:
            mmap = self.stats.stats_recorder.new_measurement_map()
            tmap = tag_map_module.TagMap()
            mmap.measure_float_put(self.request_duration, duration_ms)
            mmap.record(tmap)


# Health check utilities (enhanced with Application Insights)
class HealthChecker:
    def __init__(self):
        self.logger = get_logger("health_check")
        self.metrics = AppInsightsMetrics()

    def check_openai_service(self, openai_service) -> Dict[str, Any]:
        """Check OpenAI service health"""
        import time

        start_time = time.time()

        try:
            test_result = openai_service.get_embedding("health check test")
            is_healthy = test_result is not None
            duration_ms = (time.time() - start_time) * 1000

            self.logger.info(
                "OpenAI health check completed",
                healthy=is_healthy,
                service="azure_openai",
                duration_ms=duration_ms,
            )

            return {
                "service": "azure_openai",
                "healthy": is_healthy,
                "response_time_ms": int(duration_ms),
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "OpenAI health check failed",
                error=str(e),
                service="azure_openai",
                duration_ms=duration_ms,
            )
            return {
                "service": "azure_openai",
                "healthy": False,
                "error": str(e),
                "response_time_ms": int(duration_ms),
            }

    def check_search_service(self, search_service) -> Dict[str, Any]:
        """Check search service health"""
        import time

        start_time = time.time()

        try:
            stats = search_service.get_search_stats()
            is_healthy = stats is not None
            duration_ms = (time.time() - start_time) * 1000

            self.logger.info(
                "Search service health check completed",
                healthy=is_healthy,
                service="azure_search",
                duration_ms=duration_ms,
            )

            return {
                "service": "azure_search",
                "healthy": is_healthy,
                "document_count": stats.get("documentCount", 0) if stats else 0,
                "response_time_ms": int(duration_ms),
            }
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.logger.error(
                "Search service health check failed",
                error=str(e),
                service="azure_search",
                duration_ms=duration_ms,
            )
            return {
                "service": "azure_search",
                "healthy": False,
                "error": str(e),
                "response_time_ms": int(duration_ms),
            }
