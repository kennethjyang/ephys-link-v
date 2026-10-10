from argparse import ArgumentParser

from typer import Typer
from uvicorn import run

from ephys_link.manipulators import find_manipulators
from ephys_link.server import server

# Parse CLI.
parser = ArgumentParser()
parser.add_argument(
    "-p", "--port", type=int, default=8000, help="Server port (default: 8000)"
)
args = parser.parse_args()

app = Typer()


@app.command()
def main():
    find_manipulators()
    run(server, host="0.0.0.0", port=args.port)


# Launch.
if __name__ == "__main__":
    app()
