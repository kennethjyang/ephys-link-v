from argparse import ArgumentParser

from uvicorn import run

from ephys_link.manipulators import find_manipulators
from ephys_link.server import app

# Parse CLI.
parser = ArgumentParser()
parser.add_argument(
    "-p", "--port", type=int, default=8000, help="Server port (default: 8000)"
)
args = parser.parse_args()

# Launch.
if __name__ == "__main__":
    find_manipulators()
    run(app, host="0.0.0.0", port=args.port)
