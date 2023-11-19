import logging
from pathlib import Path

import typer

from relive_dm.server import download_all, servers

app = typer.Typer()


@app.command()
def download(path: Path = Path("assets")):
    logging.basicConfig(level=logging.INFO)
    download_all(path)


@app.command()
def list_servers():
    for server in servers:
        print(f"{server.name}:")
        print(f"  entry_url: {server.entry_url}")
        print(f"  lang_id: {server.lang_id}")


if __name__ == "__main__":
    app()
