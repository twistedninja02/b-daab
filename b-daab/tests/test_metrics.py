import pytest
from eval.metrics import (
    MetricsCalculator,
    MetricsAggregator,
    ErrorClassifier,
    ErrorCategory,
    QueryMetrics,
)


class TestCompareSql:

    def test_exact_match(self):
        exact, normalized = MetricsCalculator.compare_sql(
            "SELECT * FROM hospitals;",
            "SELECT * FROM hospitals;"
        )
        assert exact is True
        assert normalized is True

    def test_normalized_match_case(self):
        exact, normalized = MetricsCalculator.compare_sql(
            "select * from hospitals;",
            "SELECT * FROM hospitals;"
        )
        assert exact is False
        assert normalized is True

    def test_normalized_match_whitespace(self):
        exact, normalized = MetricsCalculator.compare_sql(
            "SELECT  *  FROM  hospitals;",
            "SELECT * FROM hospitals;"
        )
        assert exact is False
        assert normalized is True

    def test_no_match(self):
        exact, normalized = MetricsCalculator.compare_sql(
            "SELECT * FROM patients;",
            "SELECT * FROM hospitals;"
        )
        assert exact is False
        assert normalized is False

    def test_none_generated_returns_false(self):
        exact, normalized = MetricsCalculator.compare_sql(None, "SELECT * FROM hospitals;")
        assert exact is False
        assert normalized is False


class TestCompareResults:

    def test_exact_match(self):
        actual = [{"id": 1, "name": "Dhaka Hospital"}]
        expected = [{"id": 1, "name": "Dhaka Hospital"}]
        exact, partial, matched, exp, act = MetricsCalculator.compare_results(actual, expected)
        assert exact is True
        assert matched == 1

    def test_partial_match(self):
        actual = [{"id": 1, "name": "Dhaka Hospital"}, {"id": 2, "name": "Other"}]
        expected = [{"id": 1, "name": "Dhaka Hospital"}, {"id": 2, "name": "Wrong"}]
        exact, partial, matched, exp, act = MetricsCalculator.compare_results(actual, expected)
        assert exact is False
        assert partial is True
        assert matched == 1

    def test_no_match(self):
        actual = [{"id": 99, "name": "Wrong"}]
        expected = [{"id": 1, "name": "Dhaka Hospital"}]
        exact, partial, matched, exp, act = MetricsCalculator.compare_results(actual, expected)
        assert exact is False
        assert matched == 0

    def test_different_lengths_no_match(self):
        actual = [{"id": 1}, {"id": 2}]
        expected = [{"id": 1}]
        exact, partial, matched, exp, act = MetricsCalculator.compare_results(actual, expected)
        assert exact is False
        assert exp == 1
        assert act == 2

    def test_none_actual_returns_false(self):
        expected = [{"id": 1}]
        exact, partial, matched, exp, act = MetricsCalculator.compare_results(None, expected)
        assert exact is False
        assert partial is False
        assert matched == 0

    def test_float_tolerance(self):
        actual = [{"value": 1.00001}]
        expected = [{"value": 1.0}]
        exact, partial, matched, exp, act = MetricsCalculator.compare_results(
            actual, expected, tolerance=0.001
        )
        assert exact is True


class TestErrorClassifier:

    def test_classifies_syntax_error(self):
        primary, _ = ErrorClassifier.classify_execution_error("syntax error near SELECT")
        assert primary == ErrorCategory.SYNTAX_ERROR

    def test_classifies_table_not_found(self):
        primary, _ = ErrorClassifier.classify_execution_error("table not found: xyz")
        assert primary == ErrorCategory.TABLE_NOT_FOUND

    def test_classifies_column_not_found(self):
        primary, _ = ErrorClassifier.classify_execution_error("column not found: xyz")
        assert primary == ErrorCategory.COLUMN_NOT_FOUND

    def test_classifies_timeout(self):
        primary, _ = ErrorClassifier.classify_execution_error("timeout exceeded")
        assert primary == ErrorCategory.TIMEOUT

    def test_classifies_connection_error(self):
        primary, _ = ErrorClassifier.classify_execution_error("connection refused")
        assert primary == ErrorCategory.CONNECTION_ERROR

    def test_unknown_falls_back_to_execution_error(self):
        primary, _ = ErrorClassifier.classify_execution_error("something went wrong")
        assert primary == ErrorCategory.EXECUTION_ERROR

    def test_no_sql_generated(self):
        error = ErrorClassifier.classify_result_error(None, "SELECT 1", [], None, 0)
        assert error == ErrorCategory.NO_SQL_GENERATED


class TestMetricsAggregator:

    def _make_metric(self, query_id, result_match, execution_success, difficulty="easy", domain="healthcare"):
        m = QueryMetrics(
            query_id=query_id,
            difficulty=difficulty,
            domain=domain,
            language="bengali_standard",
            dialect="standard",
            bengali_query="test",
            ground_truth_sql="SELECT 1",
            expected_result=[],
            result_match=result_match,
            execution_success=execution_success,
            confidence_score=0.9 if result_match else 0.1,
            primary_error=ErrorCategory.NONE if result_match else ErrorCategory.WRONG_ROWS
        )
        return m

    def test_empty_list_returns_zero_metrics(self):
        agg = MetricsAggregator.aggregate([])
        assert agg.total_queries == 0
        assert agg.result_accuracy == 0.0

    def test_all_correct(self):
        metrics = [self._make_metric(f"q{i}", True, True) for i in range(4)]
        agg = MetricsAggregator.aggregate(metrics)
        assert agg.total_queries == 4
        assert agg.correct_queries == 4
        assert agg.result_accuracy == 1.0
        assert agg.execution_accuracy == 1.0

    def test_all_failed(self):
        metrics = [self._make_metric(f"q{i}", False, False) for i in range(4)]
        agg = MetricsAggregator.aggregate(metrics)
        assert agg.correct_queries == 0
        assert agg.result_accuracy == 0.0

    def test_mixed_results(self):
        correct = [self._make_metric(f"c{i}", True, True) for i in range(3)]
        failed = [self._make_metric(f"f{i}", False, False) for i in range(1)]
        agg = MetricsAggregator.aggregate(correct + failed)
        assert agg.total_queries == 4
        assert agg.correct_queries == 3
        assert agg.result_accuracy == pytest.approx(0.75)

    def test_accuracy_by_difficulty(self):
        easy = [self._make_metric(f"e{i}", True, True, difficulty="easy") for i in range(2)]
        hard = [self._make_metric(f"h{i}", False, False, difficulty="hard") for i in range(2)]
        agg = MetricsAggregator.aggregate(easy + hard)
        assert agg.accuracy_by_difficulty["easy"] == 1.0
        assert agg.accuracy_by_difficulty["hard"] == 0.0

    def test_accuracy_by_domain(self):
        health = [self._make_metric(f"h{i}", True, True, domain="healthcare") for i in range(2)]
        edu = [self._make_metric(f"e{i}", False, True, domain="education") for i in range(2)]
        agg = MetricsAggregator.aggregate(health + edu)
        assert agg.accuracy_by_domain["healthcare"] == 1.0
        assert agg.accuracy_by_domain["education"] == 0.0

    def test_error_distribution(self):
        metrics = [self._make_metric(f"q{i}", False, False) for i in range(3)]
        agg = MetricsAggregator.aggregate(metrics)
        assert ErrorCategory.WRONG_ROWS.value in agg.error_distribution
        assert agg.error_distribution[ErrorCategory.WRONG_ROWS.value] == 3
