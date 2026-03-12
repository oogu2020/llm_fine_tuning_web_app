"""CLI entry point for the customer support agent."""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.agent.graph import support_agent
from src.api.main import app as api_app
from src.core.config import settings
from src.core.logging import logger
from src.schemas.agent import AgentState
from src.schemas.email import CustomerEmail, EmailStatus
from src.services.email_service import get_email_service

console = Console()
cli = typer.Typer(help="Customer Support Email Agent CLI")


@cli.command()
def version():
    """Show version information."""
    console.print(Panel(f"[bold blue]{settings.app_name}[/bold blue] v{settings.app_version}"))


@cli.command()
def serve(
    host: str = typer.Option(settings.api_host, "--host", "-h"),
    port: int = typer.Option(settings.api_port, "--port", "-p"),
    reload: bool = typer.Option(settings.debug, "--reload", "-r"),
):
    """Start the API server."""
    import uvicorn

    console.print(Panel(f"Starting API server on {host}:{port}", style="green"))
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@cli.command()
def fetch():
    """Fetch and process unread emails from IMAP."""
    from src.api.routes.emails import process_email_through_agent

    console.print("[bold blue]Fetching unread emails...[/bold blue]")

    try:
        email_service = get_email_service()
        count = 0

        for email in email_service.fetch_unread():
            console.print(f"Processing: [cyan]{email.metadata.subject}[/cyan]")

            try:
                processed = process_email_through_agent(email)
                status_color = {
                    EmailStatus.SENT: "green",
                    EmailStatus.ESCALATED: "yellow",
                    EmailStatus.FAILED: "red",
                }.get(processed.status, "white")

                console.print(
                    f"  Result: [{status_color}]{processed.status.value}[/{status_color}]"
                )

                if processed.classification:
                    console.print(
                        f"  Intent: {processed.classification.intent.value}, "
                        f"Priority: {processed.classification.priority.value}"
                    )

                count += 1

            except Exception as e:
                console.print(f"  [red]Error: {e}[/red]")

        console.print(f"\n[bold green]Processed {count} emails[/bold green]")

    except Exception as e:
        console.print(f"[bold red]Failed: {e}[/bold red]")
        raise typer.Exit(1)


@cli.command()
def process(
    subject: str = typer.Option(..., prompt=True),
    body: str = typer.Option(..., prompt=True),
    sender: str = typer.Option(..., prompt="Customer email"),
):
    """Process a single email manually."""
    from src.api.routes.emails import process_email_through_agent
    from datetime import datetime
    from src.schemas.email import EmailContent, EmailMetadata
    from src.utils.helpers import generate_id

    console.print("[bold blue]Processing email...[/bold blue]")

    try:
        # Create email
        metadata = EmailMetadata(
            message_id=generate_id(),
            subject=subject,
            sender=sender,
            sender_name="",
            to=["support@company.com"],
            received_at=datetime.utcnow(),
        )

        content = EmailContent(body_text=body)

        email = CustomerEmail(
            id=generate_id(),
            metadata=metadata,
            content=content,
        )

        # Process
        processed = process_email_through_agent(email)

        # Display results
        table = Table(title="Processing Results")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Status", processed.status.value)

        if processed.classification:
            table.add_row("Intent", processed.classification.intent.value)
            table.add_row("Priority", processed.classification.priority.value)
            table.add_row("Confidence", str(processed.classification.confidence))

        if processed.response:
            table.add_row("Subject", processed.response.subject)
            table.add_row("Tone", processed.response.tone)

        console.print(table)

        if processed.response:
            console.print(Panel(processed.response.body, title="Drafted Response"))

    except Exception as e:
        console.print(f"[bold red]Failed: {e}[/bold red]")
        raise typer.Exit(1)


@cli.command()
def index_docs(
    docs_dir: Path = typer.Option(
        "./src/knowledge_base/documents",
        "--dir",
        "-d",
        help="Directory containing documents to index",
    ),
):
    """Index documents into the knowledge base."""
    console.print(f"[bold blue]Indexing documents from {docs_dir}...[/bold blue]")

    try:
        from src.services.kb_service import get_kb_service

        kb = get_kb_service()
        count = 0

        if not docs_dir.exists():
            console.print(f"[red]Directory not found: {docs_dir}[/red]")
            raise typer.Exit(1)

        # Index supported file types
        supported_extensions = {".txt", ".md", ".rst", ".html"}

        for file_path in docs_dir.rglob("*"):
            if file_path.suffix.lower() in supported_extensions:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    kb.add_document(
                        content=content,
                        source=str(file_path.relative_to(docs_dir)),
                        metadata={"path": str(file_path)},
                    )
                    count += 1
                    console.print(f"  [green]✓[/green] {file_path.name}")
                except Exception as e:
                    console.print(f"  [red]✗[/red] {file_path.name}: {e}")

        console.print(f"\n[bold green]Indexed {count} documents[/bold green]")

    except Exception as e:
        console.print(f"[bold red]Failed: {e}[/bold red]")
        raise typer.Exit(1)


@cli.command()
def search_kb(
    query: str = typer.Option(..., prompt=True),
    top_k: int = typer.Option(5, "--top-k", "-k"),
):
    """Search the knowledge base."""
    console.print(f"[bold blue]Searching: {query}[/bold blue]\n")

    try:
        from src.services.kb_service import get_kb_service

        kb = get_kb_service()
        results = kb.search(query, top_k=top_k)

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        for i, result in enumerate(results, 1):
            panel = Panel(
                result.content[:500] + "..." if len(result.content) > 500 else result.content,
                title=f"{i}. {result.source} (Score: {result.similarity_score:.3f})",
            )
            console.print(panel)

    except Exception as e:
        console.print(f"[bold red]Failed: {e}[/bold red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    cli()
