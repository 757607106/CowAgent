from agent.memory.storage import MemoryStorage, SearchResult
from config import conf


def test_pgvector_literal_accepts_finite_numbers():
    assert MemoryStorage._pgvector_literal([1, 0.25, -3.5]) == "[1,0.25,-3.5]"


def test_pgvector_literal_rejects_invalid_values():
    assert MemoryStorage._pgvector_literal([]) is None
    assert MemoryStorage._pgvector_literal([1.0, float("nan")]) is None
    assert MemoryStorage._pgvector_literal([1.0, "bad"]) is None


def test_merge_vector_results_keeps_best_score_per_chunk():
    primary = [
        SearchResult("MEMORY.md", 1, 1, 0.6, "primary", "memory"),
    ]
    fallback = [
        SearchResult("MEMORY.md", 1, 1, 0.9, "fallback", "memory"),
        SearchResult("OTHER.md", 1, 1, 0.5, "other", "memory"),
    ]

    merged = MemoryStorage._merge_vector_results(primary, fallback, limit=2)

    assert [item.snippet for item in merged] == ["fallback", "other"]


def test_jsonb_vector_candidate_limit_is_bounded_and_configurable(monkeypatch):
    monkeypatch.setitem(conf(), "memory_jsonb_vector_scan_limit", 12)

    assert MemoryStorage._jsonb_vector_candidate_limit(3) == 12
    assert MemoryStorage._jsonb_vector_candidate_limit(20) == 20
