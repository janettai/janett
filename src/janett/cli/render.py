"""Terminal rendering of review results."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..core.models import ReviewResult, Severity

_SEVERITY_STYLE = {
    Severity.error: "bold red",
    Severity.warning: "yellow",
    Severity.info: "cyan",
}


def render_result(result: ReviewResult, console: Console | None = None) -> None:
    console = console or Console()

    if result.skipped_reason:
        console.print(f"[dim]Review skipped: {result.skipped_reason}[/dim]")
        return

    if result.summary:
        console.print(Panel(result.summary, title="Janett review", expand=False))

    if not result.findings:
        console.print("[green]✓ No issues found.[/green]")
        return

    for f in result.findings:
        style = _SEVERITY_STYLE.get(f.severity, "white")
        header = Text()
        header.append(f"{f.severity.value.upper()}", style=style)
        header.append(f"  {f.path}:{f.line}  ", style="bold")
        header.append(f"[{f.category}]", style="dim")
        console.print(header)
        console.print(f"  {f.message}")
        if f.suggestion:
            console.print(f"  [dim]suggestion:[/dim] {f.suggestion}")
        console.print()

    counts = {
        sev: sum(1 for f in result.findings if f.severity == sev) for sev in Severity
    }
    console.print(
        f"[dim]{counts[Severity.error]} error(s), "
        f"{counts[Severity.warning]} warning(s), "
        f"{counts[Severity.info]} info — model: {result.model}[/dim]"
    )
