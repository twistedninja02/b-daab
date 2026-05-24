"""
B-DAAB Evaluation Metrics
Comprehensive evaluation framework with error categorization
"""

import logging
import re
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    SYNTAX_ERROR = "syntax_error"
    PARSE_ERROR = "parse_error"
    TABLE_NOT_FOUND = "table_not_found"
    COLUMN_NOT_FOUND = "column_not_found"
    SCHEMA_MISMATCH = "schema_mismatch"
    WRONG_JOIN = "wrong_join"
    WRONG_WHERE = "wrong_where"
    WRONG_AGGREGATION = "wrong_aggregation"
    WRONG_GROUP_BY = "wrong_group_by"
    WRONG_ORDER_BY = "wrong_order_by"
    MISSING_JOIN = "missing_join"
    MISSING_WHERE = "missing_where"
    MISSING_GROUP_BY = "missing_group_by"
    WRONG_COLUMNS = "wrong_columns"
    WRONG_ROWS = "wrong_rows"
    WRONG_VALUES = "wrong_values"
    PARTIAL_MATCH = "partial_match"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    EXECUTION_ERROR = "execution_error"
    NO_SQL_GENERATED = "no_sql_generated"
    EXTRACTION_ERROR = "extraction_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN_ERROR = "unknown_error"
    NONE = "none"


@dataclass
class QueryMetrics:
    query_id: str
    difficulty: str
    domain: str
    language: str
    dialect: str
    bengali_query: str
    ground_truth_sql: str
    expected_result: List[Dict[str, Any]]

    generated_sql: Optional[str] = None
    generation_success: bool = False
    generation_time_ms: float = 0.0
    generation_attempts: int = 1

    execution_success: bool = False
    actual_result: Optional[List[Dict[str, Any]]] = None
    execution_time_ms: float = 0.0
    execution_error: Optional[str] = None

    sql_exact_match: bool = False
    sql_normalized_match: bool = False
    result_match: bool = False
    result_partial_match: bool = False
    matched_rows: int = 0
    expected_rows: int = 0
    actual_rows: int = 0

    primary_error: Optional[ErrorCategory] = None
    secondary_errors: List[ErrorCategory] = field(default_factory=list)
    error_message: Optional[str] = None
    confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        if self.primary_error:
            result['primary_error'] = self.primary_error.value
        result['secondary_errors'] = [e.value for e in self.secondary_errors]
        return result


@dataclass
class AggregateMetrics:
    total_queries: int = 0
    correct_queries: int = 0
    partially_correct: int = 0
    failed_queries: int = 0

    exact_match_accuracy: float = 0.0
    normalized_match_accuracy: float = 0.0
    execution_accuracy: float = 0.0
    result_accuracy: float = 0.0

    accuracy_by_difficulty: Dict[str, float] = field(default_factory=dict)
    accuracy_by_domain: Dict[str, float] = field(default_factory=dict)
    accuracy_by_language: Dict[str, float] = field(default_factory=dict)
    accuracy_by_dialect: Dict[str, float] = field(default_factory=dict)

    error_distribution: Dict[str, int] = field(default_factory=dict)
    most_common_errors: List[Tuple[str, int]] = field(default_factory=list)

    avg_generation_time_ms: float = 0.0
    avg_execution_time_ms: float = 0.0
    avg_confidence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SQLNormalizer:
    @staticmethod
    def normalize(sql: str) -> str:
        sql = sql.strip()
        sql = re.sub(r'--.*?(\n|$)', '', sql)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        sql = sql.upper()
        sql = re.sub(r'\s+', ' ', sql)
        sql = re.sub(r'\s*(,|;|=|\(|\))\s*', r'\1', sql)
        return sql.strip()


class MetricsCalculator:
    @staticmethod
    def compare_sql(
        generated: Optional[str],
        ground_truth: str
    ) -> Tuple[bool, bool]:
        if not generated:
            return False, False
        exact_match = generated.strip() == ground_truth.strip()
        gen_norm = SQLNormalizer.normalize(generated)
        truth_norm = SQLNormalizer.normalize(ground_truth)
        normalized_match = gen_norm == truth_norm
        return exact_match, normalized_match

    @staticmethod
    def compare_results(
        actual: Optional[List[Dict[str, Any]]],
        expected: List[Dict[str, Any]],
        tolerance: float = 0.0001
    ) -> Tuple[bool, bool, int, int, int]:
        if not actual:
            return False, False, 0, len(expected), 0
        if len(actual) != len(expected):
            return False, False, 0, len(expected), len(actual)
        matched = 0
        for actual_row, expected_row in zip(actual, expected):
            if MetricsCalculator._rows_match(actual_row, expected_row, tolerance):
                matched += 1
        exact_match = matched == len(expected)
        partial_match = matched > 0
        return exact_match, partial_match, matched, len(expected), len(actual)

    @staticmethod
    def _rows_match(row1: Dict[str, Any], row2: Dict[str, Any], tolerance: float) -> bool:
        if len(row1) != len(row2):
            return False
        for key in row1:
            if key not in row2:
                return False
            val1, val2 = row1[key], row2[key]
            if isinstance(val1, float) and isinstance(val2, float):
                if abs(val1 - val2) > tolerance:
                    return False
            elif str(val1).strip() != str(val2).strip():
                return False
        return True


class ErrorClassifier:
    @staticmethod
    def classify_execution_error(
        error_msg: str,
        sql: Optional[str] = None
    ) -> Tuple[ErrorCategory, List[ErrorCategory]]:
        error_lower = error_msg.lower()
        if 'syntax' in error_lower or 'parse' in error_lower:
            return ErrorCategory.SYNTAX_ERROR, []
        if 'table' in error_lower and 'not found' in error_lower:
            return ErrorCategory.TABLE_NOT_FOUND, []
        if 'column' in error_lower and 'not found' in error_lower:
            return ErrorCategory.COLUMN_NOT_FOUND, []
        if 'timeout' in error_lower:
            return ErrorCategory.TIMEOUT, []
        if 'connection' in error_lower:
            return ErrorCategory.CONNECTION_ERROR, []
        return ErrorCategory.EXECUTION_ERROR, []

    @staticmethod
    def classify_result_error(
        gen_sql: Optional[str],
        truth_sql: str,
        expected: List[Dict[str, Any]],
        actual: Optional[List[Dict[str, Any]]],
        matched_rows: int
    ) -> ErrorCategory:
        if not gen_sql:
            return ErrorCategory.NO_SQL_GENERATED
        if not actual:
            return ErrorCategory.WRONG_ROWS
        if matched_rows == 0:
            return ErrorCategory.WRONG_VALUES
        if 0 < matched_rows < len(expected):
            return ErrorCategory.PARTIAL_MATCH
        return ErrorCategory.WRONG_ROWS


class MetricsAggregator:
    @staticmethod
    def aggregate(metrics_list: List[QueryMetrics]) -> AggregateMetrics:
        if not metrics_list:
            return AggregateMetrics()

        agg = AggregateMetrics(total_queries=len(metrics_list))

        correct = sum(1 for m in metrics_list if m.result_match)
        partial = sum(1 for m in metrics_list if m.result_partial_match and not m.result_match)

        agg.correct_queries = correct
        agg.partially_correct = partial
        agg.failed_queries = len(metrics_list) - correct - partial

        n = len(metrics_list)
        agg.exact_match_accuracy = correct / n
        agg.normalized_match_accuracy = sum(1 for m in metrics_list if m.sql_normalized_match) / n
        agg.execution_accuracy = sum(1 for m in metrics_list if m.execution_success) / n
        agg.result_accuracy = correct / n

        difficulties: Dict[str, List[QueryMetrics]] = {}
        for m in metrics_list:
            difficulties.setdefault(m.difficulty, []).append(m)
        for diff, mets in difficulties.items():
            agg.accuracy_by_difficulty[diff] = sum(1 for m in mets if m.result_match) / len(mets)

        domains: Dict[str, List[QueryMetrics]] = {}
        for m in metrics_list:
            domains.setdefault(m.domain, []).append(m)
        for domain, mets in domains.items():
            agg.accuracy_by_domain[domain] = sum(1 for m in mets if m.result_match) / len(mets)

        errors: Dict[str, int] = {}
        for m in metrics_list:
            if m.primary_error:
                error_name = m.primary_error.value
                errors[error_name] = errors.get(error_name, 0) + 1
        agg.error_distribution = errors
        agg.most_common_errors = sorted(errors.items(), key=lambda x: x[1], reverse=True)

        agg.avg_generation_time_ms = sum(m.generation_time_ms for m in metrics_list) / n
        agg.avg_execution_time_ms = sum(m.execution_time_ms for m in metrics_list) / n
        agg.avg_confidence_score = sum(m.confidence_score for m in metrics_list) / n

        return agg
