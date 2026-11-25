import pytest

from stt.database import TranscriptionRepository, create_db_engine, init_db


@pytest.fixture
def repo() -> TranscriptionRepository:
    engine = create_db_engine("sqlite:///:memory:")
    init_db(engine)
    return TranscriptionRepository(engine)


def test_create_and_get(repo):
    created = repo.create(title="  Standup  ", text="Kal meeting hai, please join", language="auto", source="live")
    fetched = repo.get(created.id)
    assert fetched is not None
    assert fetched.title == "Standup"
    assert fetched.source == "live"
    assert fetched.word_count == 5


def test_list_orders_newest_first_and_filters(repo):
    repo.create(title="First", text="hello world", source="live")
    repo.create(title="Second", text="namaste duniya", source="clip")
    assert [r.title for r in repo.list()] == ["Second", "First"]
    assert [r.title for r in repo.list(search="NAMASTE")] == ["Second"]
    assert [r.title for r in repo.list(source="live")] == ["First"]


def test_update(repo):
    record = repo.create(title="Old", text="old text")
    updated = repo.update(record.id, title="New", text="new text", language="hi-IN")
    assert (updated.title, updated.text, updated.language) == ("New", "new text", "hi-IN")
    assert repo.update(9999, title="x") is None


def test_update_rejects_non_editable_fields(repo):
    record = repo.create(title="T", text="t")
    with pytest.raises(ValueError):
        repo.update(record.id, source="clip")


def test_delete(repo):
    record = repo.create(title="T", text="t")
    assert repo.delete(record.id) is True
    assert repo.get(record.id) is None
    assert repo.delete(record.id) is False


@pytest.mark.parametrize("title,text", [("", "text"), ("title", "   "), ("x" * 201, "text")])
def test_validation(repo, title, text):
    with pytest.raises(ValueError):
        repo.create(title=title, text=text)


def test_stats(repo):
    repo.create(title="A", text="a")
    repo.create(title="B", text="b")
    stats = repo.stats()
    assert stats.total == 2
    assert stats.last_7_days == 2
