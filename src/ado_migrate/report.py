from dataclasses import dataclass, field


@dataclass
class ReportSection:
    title: str
    items: list[str] = field(default_factory=list)


@dataclass
class ReportData:
    dry_run: bool
    sections: list[ReportSection] = field(default_factory=list)


def render_report(data: ReportData) -> str:
    mode_label = "Dry Run" if data.dry_run else "Migration Run"

    sections_html = "\n".join(
        f"<section><h2>{section.title}</h2>"
        f"<ul>{''.join(f'<li>{item}</li>' for item in section.items)}</ul></section>"
        for section in data.sections
    )

    return (
        "<html><head><title>ADO Migration Report</title></head>"
        f"<body><h1>ADO Migration Report — {mode_label}</h1>"
        f"{sections_html}"
        "</body></html>"
    )
