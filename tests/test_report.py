from ado_migrate.report import ReportData, render_report


def test_render_report_with_no_sections_produces_valid_empty_report():
    data = ReportData(dry_run=True, sections=[])

    html = render_report(data)

    assert "<html" in html
    assert "</html>" in html


def test_render_report_reflects_dry_run_flag():
    dry_run_html = render_report(ReportData(dry_run=True, sections=[]))
    real_run_html = render_report(ReportData(dry_run=False, sections=[]))

    assert "Dry Run" in dry_run_html
    assert "Dry Run" not in real_run_html
