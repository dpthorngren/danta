import argparse
import pathlib
import sys
from .manager import Manager


def main():
    # Process the command line arguments
    parser = argparse.ArgumentParser("danta", description="Run Python functions as tasks, handling prerequisites.")
    parser.add_argument("path", type=pathlib.Path, nargs="?", default=None, help="Directory/files to run from.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])
    if args.verbose:
        print(f"Danta CLI args: {args}")
    path = args.path.expanduser()

    # Set up the manager and load target modules
    man = Manager(args.verbose)
    if path.is_file():
        man.add_module(path)
    else:
        for file in path.glob("*.py"):
            if not file.name.startswith("_"):
                man.add_module(file)

    # Execute tasks
    if args.verbose:
        man.summary()
    man.run(args.dry_run)
