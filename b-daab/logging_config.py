"""
B-DAAB Logging Configuration
Provides comprehensive logging with file rotation and console output
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import json
from datetime import datetime


@dataclass
class LoggerConfig:
    log_dir: str = "logs"
    log_level: str = "INFO"
    console_level: str = "INFO"
    max_bytes: int = 10 * 1024 * 1024
    backup_count: int = 5
    use_json: bool = False
    use_color: bool = True


class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f'{log_color}{record.levelname}{self.RESET}'
        return super().format(record)


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


class ExecutionLogger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_query_execution(
        self,
        query_id: str,
        query: str,
        success: bool,
        execution_time_ms: float,
        rows_returned: int = 0,
        error: Optional[str] = None
    ) -> None:
        if success:
            self.logger.info(
                f"Query {query_id}: SUCCESS ({execution_time_ms:.2f}ms, {rows_returned} rows)"
            )
        else:
            self.logger.error(
                f"Query {query_id}: FAILED ({execution_time_ms:.2f}ms, error={error})"
            )

    def log_batch_execution(
        self,
        batch_id: str,
        total_queries: int,
        successful: int,
        failed: int,
        total_time_ms: float
    ) -> None:
        success_rate = (successful / total_queries * 100) if total_queries > 0 else 0
        self.logger.info(
            f"Batch {batch_id}: {successful}/{total_queries} successful "
            f"({success_rate:.1f}%, {total_time_ms:.2f}ms)"
        )


class PerformanceLogger:
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def log_performance_metric(self, metric_name: str, value: float, unit: str = "ms") -> None:
        self.logger.debug(f"Performance: {metric_name}={value}{unit}")

    def log_database_stats(self, table_name: str, row_count: int, size_bytes: int) -> None:
        size_mb = size_bytes / (1024 * 1024)
        self.logger.debug(f"Database: {table_name} ({row_count} rows, {size_mb:.2f}MB)")


def initialize_logging(config: LoggerConfig) -> None:
    log_dir = Path(config.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level))

    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "b_daab.log",
        maxBytes=config.max_bytes,
        backupCount=config.backup_count
    )
    file_handler.setLevel(getattr(logging, config.log_level))

    formatter = JSONFormatter() if config.use_json else logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, config.console_level))

    if config.use_color:
        console_formatter = ColoredFormatter('%(levelname)s - %(name)s - %(message)s')
    else:
        console_formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')

    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)


def setup_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def get_execution_logger() -> ExecutionLogger:
    return ExecutionLogger(logging.getLogger('execution'))


def get_performance_logger() -> PerformanceLogger:
    return PerformanceLogger(logging.getLogger('performance'))
