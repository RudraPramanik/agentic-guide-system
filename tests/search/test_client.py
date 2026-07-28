"""P3: Qdrant client availability is live across modules."""

from src.search import client as client_mod
from src.search.client import is_qdrant_available


def test_is_qdrant_available_reflects_live_state_across_modules() -> None:
    """Importing the function (not a bool) observes live flips from another module."""
    client_mod._set_qdrant_available(False)
    assert is_qdrant_available() is False

    # Simulate another module calling the same function after a flip
    from src.search import places_index as places_index_mod

    client_mod._set_qdrant_available(True)
    assert places_index_mod.is_qdrant_available() is True

    client_mod._set_qdrant_available(False)
    assert places_index_mod.is_qdrant_available() is False
