"""Tests for normalizing report table rows."""

from bs4 import BeautifulSoup

from deapp.parsers.utils import normalize_report_table


def _normalize_table(markup: str) -> list[list[str]]:
    """Parse a small HTML fixture and normalize its table."""
    table = BeautifulSoup(markup, "html.parser").find("table")
    assert table is not None
    return normalize_report_table(table)


def test_item_carries_within_same_stage_but_resets_on_stage_change() -> None:
    matrix = _normalize_table(
        """
        <table>
          <tr><th>STAGE</th><th>PRODUCT NAME</th></tr>
          <tr><td rowspan="2">DRYING</td><td>Micro-crystalline Cellulose</td></tr>
          <tr><td></td></tr>
          <tr><td rowspan="2">DISPENSING 2</td><td></td></tr>
          <tr><td></td></tr>
        </table>
        """
    )

    assert [row[:2] for row in matrix] == [
        ["STAGE", "PRODUCT NAME"],
        ["DRYING", "Micro-crystalline Cellulose"],
        ["DRYING", "Micro-crystalline Cellulose"],
        ["DISPENSING 2", ""],
        ["DISPENSING 2", ""],
    ]


def test_item_carries_when_stage_has_a_minor_spelling_error() -> None:
    matrix = _normalize_table(
        """
        <table>
          <tr><th>STAGE</th><th>PRODUCT NAME</th></tr>
          <tr><td>BLENDING</td><td>Micro-crystalline Cellulose</td></tr>
          <tr><td>BLENDNG</td><td></td></tr>
        </table>
        """
    )

    assert matrix[2][:2] == ["BLENDNG", "Micro-crystalline Cellulose"]


def test_item_does_not_carry_between_differently_numbered_stages() -> None:
    matrix = _normalize_table(
        """
        <table>
          <tr><th>STAGE</th><th>PRODUCT NAME</th></tr>
          <tr><td>DISPENSING 1</td><td>Micro-crystalline Cellulose</td></tr>
          <tr><td>DISPENSING 2</td><td></td></tr>
        </table>
        """
    )

    assert matrix[2][:2] == ["DISPENSING 2", ""]
