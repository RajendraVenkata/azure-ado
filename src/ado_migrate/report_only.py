from ado_migrate.client import AdoClient
from ado_migrate.report import ReportSection


def detect_report_only_artifacts(
    source_client: AdoClient, source_project: str
) -> list[ReportSection]:
    release_pipelines = source_client.list_release_pipelines(source_project)
    dashboards = source_client.list_dashboards(source_project)
    artifact_feeds = source_client.list_artifact_feeds(source_project)
    used_extensions = source_client.list_used_extensions(source_project)

    return [
        ReportSection(
            title="Classic Release Pipelines",
            items=[p.name for p in release_pipelines],
        ),
        ReportSection(
            title="Dashboards",
            items=[f"{d.name} ({len(d.widgets)} widgets)" for d in dashboards],
        ),
        ReportSection(
            title="Artifact Feeds",
            items=[f.name for f in artifact_feeds],
        ),
        ReportSection(
            title="Marketplace Extensions",
            items=[e.name for e in used_extensions],
        ),
    ]
