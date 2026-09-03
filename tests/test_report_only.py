from ado_migrate.client import (
    ArtifactFeed,
    Dashboard,
    Extension,
    InMemoryFakeAdoClient,
    ReleasePipeline,
)
from ado_migrate.report_only import detect_report_only_artifacts


def test_detect_report_only_artifacts_lists_classic_release_pipelines(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    source.seed_release_pipelines(
        "SourceProject",
        [ReleasePipeline(id="rp-1", name="Deploy to Prod")],
    )

    sections = detect_report_only_artifacts(source, "SourceProject")

    release_section = next(s for s in sections if s.title == "Classic Release Pipelines")
    assert release_section.items == ["Deploy to Prod"]


def test_detect_report_only_artifacts_lists_dashboards_with_widget_counts(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    source.seed_dashboards(
        "SourceProject",
        [Dashboard(id="db-1", name="Team Overview", widgets=["Burndown", "Velocity"])],
    )

    sections = detect_report_only_artifacts(source, "SourceProject")

    dashboard_section = next(s for s in sections if s.title == "Dashboards")
    assert dashboard_section.items == ["Team Overview (2 widgets)"]


def test_detect_report_only_artifacts_lists_artifact_feeds(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    source.seed_artifact_feeds(
        "SourceProject", [ArtifactFeed(id="feed-1", name="internal-npm")]
    )

    sections = detect_report_only_artifacts(source, "SourceProject")

    feed_section = next(s for s in sections if s.title == "Artifact Feeds")
    assert feed_section.items == ["internal-npm"]


def test_detect_report_only_artifacts_lists_used_extensions(tmp_path):
    source = InMemoryFakeAdoClient(dry_run=False)
    source.seed_used_extensions(
        "SourceProject", [Extension(id="ext-1", name="SonarQube")]
    )

    sections = detect_report_only_artifacts(source, "SourceProject")

    extension_section = next(s for s in sections if s.title == "Marketplace Extensions")
    assert extension_section.items == ["SonarQube"]
