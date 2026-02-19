#!/usr/bin/env python3
"""
Command Line Interface for the ReAct Data Science Agent
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from open_data_scientist.utils.writer import _write_report
from open_data_scientist.utils.config import validate_runtime_config, load_env_file

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from open_data_scientist.codeagent import ReActDataScienceAgent

console = Console()


def get_data_directory(data_dir: Optional[str]) -> Optional[str]:
    """
    Handle data directory selection with user confirmation for current directory.
    """
    if data_dir is None:
        # No data directory specified, use current directory but ask for confirmation
        current_dir = os.getcwd()

        console.print("\n[yellow]No data directory specified.[/yellow]")
        console.print(f"[blue]Current directory:[/blue] {Path(current_dir).name}")

        # Show files in current directory
        files = list(Path(current_dir).iterdir())
        data_files = [
            f
            for f in files
            if f.is_file()
            and f.suffix.lower() in [".csv", ".json", ".txt", ".py", ".xlsx", ".xls"]
        ]

        if data_files:
            console.print(
                f"\n[green]Found {len(data_files)} potential data files:[/green]"
            )
            for file in data_files[:10]:  # Show max 10 files
                console.print(f"  • {file.name}")
            if len(data_files) > 10:
                console.print(f"  ... and {len(data_files) - 10} more files")
        else:
            console.print(
                "\n[yellow]No obvious data files found in current directory.[/yellow]"
            )

        use_current = Confirm.ask(
            "\n[bold]Important: Do you want to upload files from the current directory?[/bold]",
            default=False,
        )

        if use_current:
            return current_dir
        else:
            console.print("[yellow]Proceeding without uploading files.[/yellow]")
            return None
    else:
        # Data directory specified, validate it exists
        if not os.path.exists(data_dir):
            console.print(
                f"[bold red]Error:[/bold red] Data directory '{data_dir}' not found!"
            )
            sys.exit(1)

        if not os.path.isdir(data_dir):
            console.print(
                f"[bold red]Error:[/bold red] '{data_dir}' is not a directory!"
            )
            sys.exit(1)

        return data_dir


def validate_executor(executor: str) -> str:
    """Validate executor choice"""
    valid_executors = ["tci", "internal"]
    if executor not in valid_executors:
        console.print(
            f"[bold red]Error:[/bold red] Invalid executor '{executor}'. Must be one of: {', '.join(valid_executors)}"
        )
        sys.exit(1)
    return executor


def validate_provider(provider: str) -> str:
    valid_providers = ["openai", "together"]
    if provider not in valid_providers:
        console.print(
            f"[bold red]Error:[/bold red] Invalid provider '{provider}'. Must be one of: {', '.join(valid_providers)}"
        )
        sys.exit(1)
    return provider


def show_configuration(args) -> None:
    """Display the current configuration in a nice table"""
    table = Table(title="🤖 ReAct Data Science Agent Configuration")
    table.add_column("Parameter", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    table.add_row("Model", args.model)
    table.add_row("Provider", args.provider)
    table.add_row("Temperature", str(args.temperature))
    table.add_row("Max Output Tokens", str(args.max_output_tokens))
    table.add_row("LLM Timeout (s)", str(args.timeout))
    table.add_row("Max Iterations", str(args.iterations))
    table.add_row("Executor", args.executor)
    table.add_row(
        "Data Directory", args.data_dir or "Current directory (with confirmation)"
    )
    table.add_row("Trace Log", args.trace_path or "Disabled")

    console.print(table)
    console.print()


def main():
    """Main CLI entry point"""
    load_env_file()
    default_model = os.getenv("ODS_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-5-mini"
    parser = argparse.ArgumentParser(
        description="🤖 ReAct Data Science Agent - AI-powered data analysis assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with TCI (cloud) executor
  open-data-scientist

  # Use specific model and more iterations
  open-data-scientist --model "gpt-5-mini" --iterations 15

  # Use local Docker executor with specific data directory
  open-data-scientist --executor internal --data-dir /path/to/data

  # Legacy Together mode
  open-data-scientist --provider together --executor tci --model "deepseek-ai/DeepSeek-V3"

Execution Modes:
  tci      - Cloud execution via Together AI (requires provider=together)
  internal - Local Docker execution (requires docker-compose setup)
        """,
    )

    parser.add_argument(
        "--model",
        "-m",
        default=default_model,
        help=f"Language model to use (default: {default_model})",
    )

    parser.add_argument(
        "--iterations",
        "-i",
        type=int,
        default=20,
        help="Maximum number of reasoning iterations (default: 20)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="LLM sampling temperature (default: 0.0)",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=4000,
        help="Maximum output tokens per LLM call (default: 4000)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="LLM request timeout in seconds (default: 120)",
    )

    parser.add_argument(
        "--executor",
        "-e",
        choices=["tci", "internal"],
        default="internal",
        help="Code execution mode: 'tci' for cloud, 'internal' for local Docker (default: internal)",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "together"],
        default="openai",
        help="LLM provider: 'openai' (default) or 'together'",
    )

    parser.add_argument(
        "--data-dir",
        "-d",
        help="Directory containing data files to upload. If not specified, will prompt to use current directory.",
    )

    parser.add_argument(
        "--session-id", "-s", help="Reuse an existing session ID (optional)"
    )

    parser.add_argument(
        "--write-report",
        "-w",
        action="store_true",
        help="Write a report to a file (default: False)",
    )
    parser.add_argument(
        "--save-trace",
        action="store_true",
        help="Save query/execution trace as JSONL and a human-readable markdown log in the current directory",
    )

    args = parser.parse_args()

    # Validate inputs
    validate_executor(args.executor)
    validate_provider(args.provider)

    if args.iterations < 1:
        console.print("[bold red]Error:[/bold red] Iterations must be at least 1")
        sys.exit(1)
    if args.max_output_tokens < 1:
        console.print("[bold red]Error:[/bold red] --max-output-tokens must be at least 1")
        sys.exit(1)
    if args.timeout < 1:
        console.print("[bold red]Error:[/bold red] --timeout must be at least 1")
        sys.exit(1)

    # Handle data directory
    data_dir = get_data_directory(args.data_dir)

    trace_path = None
    trace_base = None
    if args.save_trace:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        trace_base = str(Path.cwd() / f"log-trace_{timestamp}")
        trace_path = f"{trace_base}.jsonl"

    # Show configuration
    # Update args for display
    args.data_dir = (Path(data_dir).name if data_dir else "None (no files will be uploaded)")
    args.trace_path = trace_base
    show_configuration(args)

    # Ask for confirmation
    if not Confirm.ask("\n[bold]Proceed with these settings?[/bold]", default=True):
        console.print("[yellow]Cancelled by user.[/yellow]")
        sys.exit(0)

    # Welcome message
    welcome_text = "🚀 Starting ReAct Data Science Agent"
    if data_dir:
        welcome_text += f"\n📁 Data from: {Path(data_dir).name}"
    welcome_text += f"\n🧠 Model: {args.model}"
    welcome_text += f"\n⚡ Executor: {args.executor.upper()}"
    if trace_base:
        welcome_text += f"\nTrace Log: {Path(trace_base).name}"

    welcome_panel = Panel(
        welcome_text,
        title="🤖 ReAct Data Science Agent",
        border_style="bold blue",
        expand=False,
    )
    console.print(welcome_panel)

    try:
        validate_runtime_config(
            provider=args.provider,
            executor=args.executor,
            model=args.model,
        )
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {str(exc)}")
        sys.exit(1)

    # Create the agent
    try:
        agent = ReActDataScienceAgent(
            session_id=args.session_id,
            model=args.model,
            max_iterations=args.iterations,
            executor=args.executor,
            provider=args.provider,
            data_dir=data_dir,
            trace_path=trace_path,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
            timeout=args.timeout,
        )

    except Exception as e:
        console.print(f"[bold red]Error creating agent:[/bold red] {str(e)}")
        sys.exit(1)

    # Interactive task input
    console.print("\n" + "=" * 80)
    console.print(
        "[bold green]Agent ready! Enter your data science task below.[/bold green]"
    )
    console.print("[dim]Type 'quit' or 'exit' to stop, or press Ctrl+C[/dim]")
    console.print("=" * 80 + "\n")

    try:
        while True:
            task = Prompt.ask(
                "[bold cyan]🎯 What would you like me to analyze?[/bold cyan]",
                default="",
            )

            if task.lower() in ["quit", "exit", "q"]:
                console.print("[yellow]Goodbye! 👋[/yellow]")
                break

            if not task.strip():
                console.print("[yellow]Please enter a task or 'quit' to exit.[/yellow]")
                continue

            # Run the analysis
            console.print("\n" + "=" * 80)
            result = agent.run(task)
            console.print("=" * 80 + "\n")

            if args.write_report:
                _write_report(
                    user_input=task,
                    result=result,
                    history=agent.history,
                    model=args.model,
                    provider=args.provider,
                    temperature=args.temperature,
                    max_output_tokens=min(args.max_output_tokens, 3000),
                    timeout=args.timeout,
                )

            # Ask if user wants to continue
            if not Confirm.ask(
                "[bold]Would you like to run another analysis?[/bold]", default=True
            ):
                console.print("[green]Task completed successfully! 🎉[/green]")
                break

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user. Goodbye! 👋[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
