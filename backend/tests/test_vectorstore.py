from app.vectorstore import VectorStore


def test_add_empty_returns_zero(store: VectorStore) -> None:
    assert store.add("a.txt", []) == 0
    assert store.list_sources() == {}


def test_search_empty_store(store: VectorStore) -> None:
    assert store.search("anything", 3) == []


def test_add_and_search_ranks_best_match_first(store: VectorStore) -> None:
    store.add("pets.txt", ["cats purr softly", "dogs bark loudly"])
    hits = store.search("cats purr softly", 2)
    assert hits[0].text == "cats purr softly"
    assert hits[0].source == "pets.txt"
    assert hits[0].distance <= hits[1].distance


def test_list_sources_counts_chunks(store: VectorStore) -> None:
    store.add("a.txt", ["one", "two"])
    store.add("b.txt", ["three"])
    assert store.list_sources() == {"a.txt": 2, "b.txt": 1}


def test_delete_source_removes_only_that_source(store: VectorStore) -> None:
    store.add("a.txt", ["one"])
    store.add("b.txt", ["two"])
    store.delete_source("a.txt")
    assert store.list_sources() == {"b.txt": 1}


def test_search_filters_by_sources(store: VectorStore) -> None:
    store.add("a.txt", ["shared words here"])
    store.add("b.txt", ["shared words here"])
    hits = store.search("shared words here", 5, sources=["b.txt"])
    assert {h.source for h in hits} == {"b.txt"}
