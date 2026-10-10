from typing import Annotated

import typer
from uvicorn import run

from ephys_link.manipulators import find_manipulators
from ephys_link.server import server

app = typer.Typer()


@app.command()
def main(
    port: Annotated[int, typer.Option("-p", "--port", help="Server port")] = 8000,
    num_fake_manipulators: Annotated[
        int,
        typer.Option(
            "-f", "--num-fake-manipulators", help="Number of fake manipulators to spawn"
        ),
    ] = 0,
) -> None:
    """Launch the ephys-link server."""
    find_manipulators(num_fake_manipulators)
    run(server, host="0.0.0.0", port=port)


# Launch.
if __name__ == "__main__":
    app()
