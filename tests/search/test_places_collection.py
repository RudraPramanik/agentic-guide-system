"""Settings + places_collection accessor contracts."""

from __future__ import annotations

from unittest.mock import patch

from src.search.client import collection_uses_hybrid_schema, places_collection


def test_places_collection_reads_settings() -> None:
    with patch(
        "src.search.client.get_settings",
        return_value=type(
            "S",
            (),
            {
                "QDRANT_PLACES_COLLECTION": "places_v2",
                "QDRANT_PLACES_COLLECTION_V2": "places_v2",
            },
        )(),
    ):
        assert places_collection() == "places_v2"
        assert collection_uses_hybrid_schema() is True


def test_legacy_collection_is_not_hybrid_schema() -> None:
    with patch(
        "src.search.client.get_settings",
        return_value=type(
            "S",
            (),
            {
                "QDRANT_PLACES_COLLECTION": "places",
                "QDRANT_PLACES_COLLECTION_V2": "places_v2",
            },
        )(),
    ):
        assert places_collection() == "places"
        assert collection_uses_hybrid_schema() is False


def test_settings_defaults_include_hybrid_knobs() -> None:
    from src.config import Settings

    fields = Settings.model_fields
    assert "QDRANT_PLACES_COLLECTION_V2" in fields
    assert fields["QDRANT_PLACES_COLLECTION_V2"].default == "places_v2"
    assert fields["SEARCH_SPARSE_ENABLED"].default is True
    assert fields["SEARCH_RRF_K"].default == 60
