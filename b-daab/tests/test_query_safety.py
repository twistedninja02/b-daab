import pytest
from executor import QuerySanitizer, QueryType


class TestQueryTypeDetection:

    def test_detects_select(self):
        assert QuerySanitizer.detect_query_type("SELECT * FROM hospitals") == QueryType.SELECT

    def test_detects_insert(self):
        assert QuerySanitizer.detect_query_type("INSERT INTO hospitals VALUES (1)") == QueryType.INSERT

    def test_detects_update(self):
        assert QuerySanitizer.detect_query_type("UPDATE hospitals SET name='x'") == QueryType.UPDATE

    def test_detects_delete(self):
        assert QuerySanitizer.detect_query_type("DELETE FROM hospitals") == QueryType.DELETE

    def test_detects_drop(self):
        assert QuerySanitizer.detect_query_type("DROP TABLE hospitals") == QueryType.DROP

    def test_case_insensitive(self):
        assert QuerySanitizer.detect_query_type("select * from hospitals") == QueryType.SELECT

    def test_unknown_returns_unknown(self):
        assert QuerySanitizer.detect_query_type("PRAGMA table_info(hospitals)") == QueryType.UNKNOWN


class TestReadOnly:

    def test_select_is_read_only(self):
        assert QuerySanitizer.is_read_only("SELECT * FROM hospitals") is True

    def test_insert_is_not_read_only(self):
        assert QuerySanitizer.is_read_only("INSERT INTO hospitals VALUES (1)") is False

    def test_delete_is_not_read_only(self):
        assert QuerySanitizer.is_read_only("DELETE FROM hospitals") is False

    def test_drop_is_not_read_only(self):
        assert QuerySanitizer.is_read_only("DROP TABLE hospitals") is False


class TestSanitize:

    def test_removes_line_comments(self):
        sql = "SELECT * FROM hospitals -- this is a comment"
        result = QuerySanitizer.sanitize(sql)
        assert "--" not in result

    def test_collapses_whitespace(self):
        sql = "SELECT   *   FROM   hospitals"
        result = QuerySanitizer.sanitize(sql)
        assert "  " not in result

    def test_strips_newlines(self):
        sql = "SELECT *\nFROM hospitals"
        result = QuerySanitizer.sanitize(sql)
        assert "\n" not in result


class TestValidateSafeQuery:

    def test_select_is_safe(self):
        is_safe, error = QuerySanitizer.validate_safe_query("SELECT * FROM hospitals")
        assert is_safe is True
        assert error is None

    def test_insert_is_not_safe(self):
        is_safe, error = QuerySanitizer.validate_safe_query("INSERT INTO hospitals VALUES (1)")
        assert is_safe is False
        assert error is not None

    def test_drop_is_not_safe(self):
        is_safe, error = QuerySanitizer.validate_safe_query("DROP TABLE hospitals")
        assert is_safe is False
        assert "DROP" in error or "SELECT" in error

    def test_delete_is_not_safe(self):
        is_safe, error = QuerySanitizer.validate_safe_query("DELETE FROM hospitals")
        assert is_safe is False

    def test_select_with_where_is_safe(self):
        is_safe, _ = QuerySanitizer.validate_safe_query(
            "SELECT * FROM hospitals WHERE city = 'Dhaka'"
        )
        assert is_safe is True

    def test_select_with_join_is_safe(self):
        is_safe, _ = QuerySanitizer.validate_safe_query(
            "SELECT h.name, COUNT(p.id) FROM hospitals h LEFT JOIN patients p ON h.id = p.hospital_id GROUP BY h.id"
        )
        assert is_safe is True
