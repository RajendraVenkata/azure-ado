import pytest

from ado_migrate.client import InMemoryFakeAdoClient
from ado_migrate.mutation import TransientError


def test_transient_failure_is_retried_and_succeeds(tmp_path):
    client = InMemoryFakeAdoClient(dry_run=False)
    client.queue_failure(TransientError("rate limited"))

    result = client.create_placeholder("widget")

    assert result == "dest-widget"
    assert len(client.mutation_log) == 1
    assert client.mutation_log[0].executed is True


def test_persistent_failure_raises_immediately_without_retry(tmp_path):
    client = InMemoryFakeAdoClient(dry_run=False)
    client.queue_failure(RuntimeError("bad request"))

    with pytest.raises(RuntimeError, match="bad request"):
        client.create_placeholder("widget")

    assert client.created == []
    assert len(client.mutation_log) == 1
    assert client.mutation_log[0].executed is False


def test_transient_failure_exhausting_retries_raises(tmp_path):
    client = InMemoryFakeAdoClient(dry_run=False)
    client.queue_failure(TransientError("rate limited 1"))
    client.queue_failure(TransientError("rate limited 2"))
    client.queue_failure(TransientError("rate limited 3"))

    with pytest.raises(TransientError, match="rate limited 3"):
        client.create_placeholder("widget")

    assert client.created == []
    assert len(client.mutation_log) == 1
    assert client.mutation_log[0].executed is False
