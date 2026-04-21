from __future__ import annotations

import click


@click.group()
def cli() -> None:
    pass


@cli.command()
def start() -> None:
    """Start the worker daemon."""
    click.echo("worker started")


@cli.command()
def stop() -> None:
    """Stop the worker daemon."""
    click.echo("worker stopped")
