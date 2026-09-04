from ado_migrate.seed_data import generate_seed_plan


def test_generate_seed_plan_includes_a_nested_area_path():
    plan = generate_seed_plan()

    assert any("/" in path for path in plan.area_paths)


def test_generate_seed_plan_includes_a_nested_iteration_path():
    plan = generate_seed_plan()

    assert any("/" in iteration.path for iteration in plan.iteration_paths)


def test_generate_seed_plan_creates_two_repos_with_three_to_five_commits_each():
    plan = generate_seed_plan()

    assert len(plan.repos) == 2
    for repo in plan.repos:
        assert 3 <= len(repo.commits) <= 5
        for commit in repo.commits:
            assert commit.message
            assert commit.files


def test_generate_seed_plan_creates_the_requested_number_of_work_items():
    plan = generate_seed_plan(work_item_count=7)

    assert len(plan.work_items) == 7


def test_generate_seed_plan_defaults_to_ten_work_items():
    plan = generate_seed_plan()

    assert len(plan.work_items) == 10


def test_generate_seed_plan_links_one_work_item_to_another():
    plan = generate_seed_plan()

    work_item_ids = {wi.id for wi in plan.work_items}
    work_item_links = [
        link
        for wi in plan.work_items
        for link in wi.links
        if link.link_type == "work_item"
    ]

    assert work_item_links
    for link in work_item_links:
        assert link.target in work_item_ids


def test_generate_seed_plan_links_one_work_item_to_a_pull_request_in_a_generated_repo():
    plan = generate_seed_plan()

    repo_names = {repo.name for repo in plan.repos}
    pull_request_links = [
        link
        for wi in plan.work_items
        for link in wi.links
        if link.link_type == "pull_request"
    ]

    assert pull_request_links
    for link in pull_request_links:
        repo_name, _, pr_number = link.target.partition(":")
        assert repo_name in repo_names
        assert pr_number


def test_generate_seed_plan_gives_one_work_item_an_attachment():
    plan = generate_seed_plan()

    work_items_with_attachments = [wi for wi in plan.work_items if wi.attachments]

    assert work_items_with_attachments
    attachment = work_items_with_attachments[0].attachments[0]
    assert attachment.name
    assert attachment.content
