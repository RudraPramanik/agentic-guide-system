"""P3: Place.tags vs Place.enriched_tags are distinct columns."""

from src.places.models import Place


def test_tags_and_enriched_tags_are_distinct_columns() -> None:
    cols = {c.name: c for c in Place.__table__.columns}
    assert "tags" in cols
    assert "enriched_tags" in cols
    assert cols["tags"] is not cols["enriched_tags"]
