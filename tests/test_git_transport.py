from ado_migrate.git_transport import InMemoryFakeGitTransport


def test_dry_run_records_intent_without_executing_push():
    transport = InMemoryFakeGitTransport(dry_run=True)

    transport.push_mirror("https://source/repo.git", "https://dest/repo.git")

    assert transport.pushed == []
    assert len(transport.mutation_log) == 1
    assert transport.mutation_log[0].executed is False


def test_real_run_executes_push_and_records_it():
    transport = InMemoryFakeGitTransport(dry_run=False)

    transport.push_mirror("https://source/repo.git", "https://dest/repo.git")

    assert transport.pushed == [("https://source/repo.git", "https://dest/repo.git")]
    assert len(transport.mutation_log) == 1
    assert transport.mutation_log[0].executed is True
