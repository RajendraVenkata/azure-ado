from ado_migrate.client import InMemoryFakeAdoClient


def test_dry_run_records_intent_without_executing_mutation():
    client = InMemoryFakeAdoClient(dry_run=True)

    result = client.create_placeholder(name="widget")

    assert result is None
    assert client.created == []
    assert len(client.mutation_log) == 1
    assert client.mutation_log[0].executed is False
    assert "widget" in client.mutation_log[0].description


def test_real_run_executes_mutation_and_records_it():
    client = InMemoryFakeAdoClient(dry_run=False)

    result = client.create_placeholder(name="widget")

    assert result == "dest-widget"
    assert client.created == ["dest-widget"]
    assert len(client.mutation_log) == 1
    assert client.mutation_log[0].executed is True
