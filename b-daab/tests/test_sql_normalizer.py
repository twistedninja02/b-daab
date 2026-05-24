import pytest
from eval.metrics import SQLNormalizer


class TestSQLNormalizer:

    def test_uppercase(self):
        result = SQLNormalizer.normalize("select * from hospitals")
        assert result == result.upper()

    def test_strips_whitespace(self):
        result = SQLNormalizer.normalize("  SELECT * FROM hospitals  ")
        assert result == result.strip()

    def test_collapses_internal_whitespace(self):
        result = SQLNormalizer.normalize("SELECT   *   FROM   hospitals")
        assert "  " not in result

    def test_removes_line_comments(self):
        sql = "SELECT * FROM hospitals -- get all\nWHERE city = 'Dhaka'"
        result = SQLNormalizer.normalize(sql)
        assert "--" not in result
        assert "GET ALL" not in result

    def test_removes_block_comments(self):
        sql = "SELECT /* fetch all */ * FROM hospitals"
        result = SQLNormalizer.normalize(sql)
        assert "FETCH ALL" not in result

    def test_equivalent_queries_normalize_equally(self):
        q1 = "SELECT * FROM hospitals;"
        q2 = "select  *  from  hospitals ;"
        assert SQLNormalizer.normalize(q1) == SQLNormalizer.normalize(q2)

    def test_different_queries_differ_after_normalization(self):
        q1 = "SELECT * FROM hospitals"
        q2 = "SELECT * FROM patients"
        assert SQLNormalizer.normalize(q1) != SQLNormalizer.normalize(q2)

    def test_newlines_collapsed(self):
        sql = "SELECT *\nFROM\nhospitals"
        result = SQLNormalizer.normalize(sql)
        assert "\n" not in result
