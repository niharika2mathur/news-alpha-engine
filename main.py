#!/usr/bin/env python3
# ============================================================
# main.py – News Alpha Engine Entry Point
# ============================================================

import asyncio
import argparse
import sys
import uvicorn
from loguru import logger
from rich.console import Console

console = Console()

BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║          📈  NEWS ALPHA ENGINE  v1.0                            ║
║          AI-Powered Stock Market Intelligence System             ║
║          Processing 800+ Articles Daily → Alpha Signals          ║
╚══════════════════════════════════════════════════════════════════╝
"""


def setup_logging():
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{message}</cyan>",
        level="INFO",
        colorize=True,
    )
    logger.add(
        "logs/pipeline_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
        compression="gz",
    )


async def run_pipeline(args):
    """Run the full daily pipeline."""
    from pipeline.orchestrator import PipelineOrchestrator

    pipe = PipelineOrchestrator()
    result = await pipe.run_full_pipeline(
        run_ingestion=not args.skip_ingestion,
        run_analysis=not args.skip_analysis,
        run_scoring=True,
        run_ranking=True,
        max_articles=args.max_articles,
    )
    return result


async def run_scheduler():
    """Start the automated pipeline scheduler."""
    from pipeline.orchestrator import PipelineOrchestrator, setup_scheduler

    pipe = PipelineOrchestrator()
    scheduler = setup_scheduler(pipe)
    scheduler.start()

    console.print("[green]✓ Scheduler started. Pipeline will run automatically.[/green]")
    console.print("  08:00 IST – Full pipeline (800+ articles)")
    console.print("  12:00 IST – Midday update")
    console.print("  15:30 IST – EOD update")

    # Run once immediately
    await pipe.run_full_pipeline()

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        scheduler.shutdown()
        console.print("[yellow]Scheduler stopped.[/yellow]")


async def demo_graph():
    """Demonstrate knowledge graph capabilities."""
    from graph.knowledge_graph import get_graph
    from graph.event_engine import EventDetectionEngine, EXAMPLE_CHAINS
    from rich.table import Table

    graph = get_graph()
    stats = graph.get_stats()

    console.print(f"\n[bold cyan]Knowledge Graph Stats:[/bold cyan]")
    console.print(f"  Nodes: {stats['nodes']} | Edges: {stats['edges']}")
    console.print(f"  Companies: {stats['companies']} | Industries: {stats['industries']}")

    # Demo: Lithium price shock
    console.print("\n[bold yellow]Demo: Lithium price +20% shock propagation:[/bold yellow]")
    effects = graph.propagate_commodity_shock("Lithium", 20)
    table = Table()
    table.add_column("Industry", style="cyan")
    table.add_column("Direction")
    table.add_column("Magnitude")
    table.add_column("Hop")
    table.add_column("Mechanism", max_width=60)

    for e in effects[:8]:
        color = "green" if e.direction == "positive" else "red"
        table.add_row(
            e.target,
            f"[{color}]{e.direction}[/{color}]",
            f"{e.magnitude:.2f}",
            str(e.hop),
            e.mechanism[:60]
        )
    console.print(table)

    # Demo: Supply chain example chains
    console.print("\n[bold yellow]Example Propagation Chains:[/bold yellow]")
    for name, chain in EXAMPLE_CHAINS.items():
        console.print(f"\n[cyan]{chain['trigger']}:[/cyan]")
        for step in chain["chain"]:
            console.print(f"  → {step}")


async def analyze_single(title: str, content: str):
    """Analyze a single article from CLI."""
    from analysis.llm_engine import LLMAnalysisEngine

    engine = LLMAnalysisEngine()
    article = {"id": 0, "title": title, "content": content, "source": "CLI", "published_at": "now"}

    console.print(f"[bold]Analyzing:[/bold] {title[:80]}...")
    intelligence = await engine.analyze_article(article)

    console.print(f"\n[bold green]Results:[/bold green]")
    console.print(f"  Event Type:    {intelligence.event_type}")
    console.print(f"  Sentiment:     {intelligence.sentiment}")
    console.print(f"  Bullish Score: {intelligence.bullish_score:.1f}/10")
    console.print(f"  Bearish Score: {intelligence.bearish_score:.1f}/10")
    console.print(f"  Net Score:     {intelligence.net_score:+.1f}")
    console.print(f"\n  Summary: {intelligence.full_report.get('ai_summary', '')}")
    console.print(f"\n  Companies: {[c['name'] for c in intelligence.companies_mentioned[:3]]}")
    console.print(f"  Industries: {intelligence.industries_affected[:3]}")


def main():
    console.print(BANNER)

    parser = argparse.ArgumentParser(
        description="News Alpha Engine – AI Stock Market Intelligence",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  pipeline   Run the full daily pipeline once
  server     Start the FastAPI API server
  dashboard  Launch the Streamlit dashboard
  scheduler  Start automated scheduled pipeline
  graph      Demo the knowledge graph
  analyze    Analyze a single article (interactive)

Examples:
  python main.py pipeline
  python main.py pipeline --max-articles 50
  python main.py server --port 8000
  python main.py dashboard
  python main.py graph
        """
    )

    parser.add_argument("command", choices=["pipeline", "server", "dashboard", "scheduler", "graph", "analyze"])
    parser.add_argument("--port", type=int, default=8000, help="API server port")
    parser.add_argument("--host", default="0.0.0.0", help="API server host")
    parser.add_argument("--max-articles", type=int, default=None, help="Limit articles for testing")
    parser.add_argument("--skip-ingestion", action="store_true", help="Skip news ingestion")
    parser.add_argument("--skip-analysis", action="store_true", help="Skip LLM analysis")

    args = parser.parse_args()
    setup_logging()

    if args.command == "pipeline":
        import os
        os.makedirs("logs", exist_ok=True)
        result = asyncio.run(run_pipeline(args))
        console.print(f"\n[bold green]Pipeline complete![/bold green] Stats: {result}")

    elif args.command == "server":
        console.print(f"[bold green]Starting API server on {args.host}:{args.port}[/bold green]")
        console.print(f"  API docs: http://localhost:{args.port}/docs")
        uvicorn.run(
            "api.main:app",
            host=args.host,
            port=args.port,
            reload=False,
            log_level="info"
        )

    elif args.command == "dashboard":
        import subprocess
        console.print("[bold green]Launching Streamlit Dashboard...[/bold green]")
        subprocess.run(["streamlit", "run", "dashboard/app.py", "--server.port", "8501"])

    elif args.command == "scheduler":
        asyncio.run(run_scheduler())

    elif args.command == "graph":
        asyncio.run(demo_graph())

    elif args.command == "analyze":
        title = input("Article title: ")
        content = input("Article content (or press Enter to use title only): ") or title
        asyncio.run(analyze_single(title, content))


if __name__ == "__main__":
    main()
