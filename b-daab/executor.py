"""
B-DAAB Query Executor
Executes SQL queries safely with error handling and result validation
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import time

from db import DatabaseLoader, DatabaseExecutionError

logger = logging.getLogger(__name__)


class QueryType(Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"
    DROP = "DROP"
    ALTER = "ALTER"
    UNKNOWN = "UNKNOWN"


class QuerySafetyError(Exception):
    pass


@dataclass
class QueryExecutionMetrics:
    execution_time_ms: float = 0.0
    result_rows: int = 0
    result_size_bytes: int = 0
    query_type: str = ""
    table_accessed: Optional[str] = None
    has_join: bool = False
    has_subquery: bool = False
    has_aggregation: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryResult:
    success: bool
    query: str
    query_type: str

    rows: Optional[List[Tuple[Any, ...]]] = None
    rows_dict: Optional[List[Dict[str, Any]]] = None
    column_names: Optional[List[str]] = None
    row_count: int = 0

    error: Optional[str] = None
    error_type: Optional[str] = None
    error_code: Optional[str] = None

    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    execution_time_ms: float = 0.0
    metrics: QueryExecutionMetrics = field(default_factory=QueryExecutionMetrics)

    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['metrics'] = self.metrics.to_dict()
        return result

    def __str__(self) -> str:
        if self.success:
            return (
                f"QueryResult(success=True, rows={self.row_count}, "
                f"time={self.execution_time_ms:.2f}ms)"
            )
        return f"QueryResult(success=False, error={self.error_type}: {self.error})"


class QuerySanitizer:
    DANGEROUS_KEYWORDS = {
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE',
        'EXEC', 'EXECUTE', 'SCRIPT', 'JAVASCRIPT'
    }
    ALLOWED_KEYWORDS = {'SELECT', 'WITH', 'PRAGMA', 'EXPLAIN'}

    @staticmethod
    def detect_query_type(query: str) -> QueryType:
        query = QuerySanitizer._remove_comments(query).strip()
        match = re.match(r'^\s*(\w+)', query, re.IGNORECASE)
        if not match:
            return QueryType.UNKNOWN
        keyword = match.group(1).upper()
        try:
            return QueryType[keyword]
        except KeyError:
            return QueryType.UNKNOWN

    @staticmethod
    def is_read_only(query: str) -> bool:
        query_type = QuerySanitizer.detect_query_type(query)
        return query_type in {QueryType.SELECT, QueryType.UNKNOWN}

    @staticmethod
    def sanitize(query: str) -> str:
        query = QuerySanitizer._remove_comments(query)
        query = re.sub(r'\s+', ' ', query)
        query = query.replace('\n', ' ').replace('\r', ' ')
        return query.strip()

    @staticmethod
    def _remove_comments(query: str) -> str:
        query = re.sub(r'--.*?(\n|$)', '\n', query)
        query = re.sub(r'/\*.*?\*/', '', query, flags=re.DOTALL)
        return query

    @staticmethod
    def validate_safe_query(query: str) -> Tuple[bool, Optional[str]]:
        query_type = QuerySanitizer.detect_query_type(query)
        if not QuerySanitizer.is_read_only(query):
            return False, f"Only SELECT queries are allowed. Got: {query_type.value}"
        upper_query = query.upper()
        for keyword in QuerySanitizer.DANGEROUS_KEYWORDS:
            if re.search(rf'\b{keyword}\b', upper_query):
                return False, f"Dangerous keyword found: {keyword}"
        return True, None


class QueryExecutor:
    def __init__(self, db: DatabaseLoader, verbose: bool = False):
        self.db = db
        self.verbose = verbose
        self.execution_history: List[QueryResult] = []
        self.execution_count = 0
        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    def execute(
        self,
        query: str,
        safety_check: bool = True,
        return_dict: bool = False,
        timeout: Optional[float] = None
    ) -> QueryResult:
        self.execution_count += 1
        start_time = time.time()

        logger.info(f"[Query #{self.execution_count}] Executing: {query[:80]}...")

        result = QueryResult(
            success=False,
            query=query,
            query_type="UNKNOWN"
        )

        try:
            sanitized_query = QuerySanitizer.sanitize(query)
            result.query = sanitized_query

            query_type = QuerySanitizer.detect_query_type(sanitized_query)
            result.query_type = query_type.value
            result.metrics.query_type = query_type.value

            if safety_check:
                is_safe, error_msg = QuerySanitizer.validate_safe_query(sanitized_query)
                if not is_safe:
                    logger.warning(f"Query failed safety check: {error_msg}")
                    raise QuerySafetyError(error_msg)

            if return_dict:
                rows_dict = self.db.execute_query_dict(sanitized_query)
                result.rows_dict = rows_dict
                result.rows = [tuple(d.values()) for d in rows_dict]
                if rows_dict:
                    result.column_names = list(rows_dict[0].keys())
            else:
                rows = self.db.execute_query(sanitized_query)
                result.rows = rows
                try:
                    db_result = self.db.connection.execute(sanitized_query)
                    result.column_names = [desc[0] for desc in db_result.description]
                except Exception:
                    result.column_names = None

            result.row_count = len(result.rows) if result.rows else 0
            result.success = True

            self._calculate_metrics(result, sanitized_query)

            logger.info(
                f"✓ Query #{self.execution_count} executed successfully "
                f"({result.row_count} rows, {result.execution_time_ms:.2f}ms)"
            )

        except QuerySafetyError as e:
            result.error = str(e)
            result.error_type = "SAFETY_ERROR"
            logger.error(f"✗ Query failed safety check: {e}")

        except DatabaseExecutionError as e:
            result.error = str(e)
            result.error_type = "EXECUTION_ERROR"
            logger.error(f"✗ Query execution error: {e}")

        except Exception as e:
            result.error = str(e)
            result.error_type = type(e).__name__
            result.error_code = getattr(e, 'code', None)
            logger.error(f"✗ Query failed: {type(e).__name__}: {e}")

        finally:
            result.execution_time_ms = (time.time() - start_time) * 1000
            self.execution_history.append(result)

        return result

    def execute_batch(
        self,
        queries: List[str],
        stop_on_error: bool = False
    ) -> List[QueryResult]:
        logger.info(f"Executing batch of {len(queries)} queries")
        results = []
        for i, query in enumerate(queries, 1):
            logger.info(f"  [{i}/{len(queries)}]")
            result = self.execute(query)
            results.append(result)
            if stop_on_error and not result.success:
                logger.warning(f"Stopping batch execution due to error in query {i}")
                break
        logger.info(f"✓ Batch execution complete ({len(results)} queries)")
        return results

    def _calculate_metrics(self, result: QueryResult, query: str) -> None:
        query_upper = query.upper()
        result.metrics.has_join = bool(re.search(r'\bJOIN\b', query_upper))
        result.metrics.has_subquery = bool(re.search(r'\(SELECT', query_upper))
        result.metrics.has_aggregation = bool(
            re.search(r'\b(SUM|COUNT|AVG|MIN|MAX|GROUP_CONCAT)\b', query_upper)
        )
        if result.rows:
            result.metrics.result_rows = len(result.rows)
            result.metrics.result_size_bytes = sum(
                len(str(row).encode('utf-8')) for row in result.rows
            )

    def get_execution_stats(self) -> Dict[str, Any]:
        successful = sum(1 for r in self.execution_history if r.success)
        failed = len(self.execution_history) - successful
        execution_times = [r.execution_time_ms for r in self.execution_history if r.success]
        return {
            'total_queries': self.execution_count,
            'successful_queries': successful,
            'failed_queries': failed,
            'success_rate': successful / self.execution_count if self.execution_count > 0 else 0,
            'avg_execution_time_ms': sum(execution_times) / len(execution_times) if execution_times else 0,
            'min_execution_time_ms': min(execution_times) if execution_times else 0,
            'max_execution_time_ms': max(execution_times) if execution_times else 0,
            'total_rows_returned': sum(r.row_count for r in self.execution_history),
        }

    def get_error_summary(self) -> Dict[str, int]:
        errors: Dict[str, int] = {}
        for result in self.execution_history:
            if not result.success and result.error_type:
                errors[result.error_type] = errors.get(result.error_type, 0) + 1
        return errors

    def clear_history(self) -> None:
        self.execution_history.clear()
        logger.debug("Cleared execution history")
