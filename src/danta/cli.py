import argparse
import pathlib
import sys
from .manager import Manager


def main():
    parser = argparse.ArgumentParser("danta", description="Run Python functions as tasks, handling prerequisites.")
    parser.add_argument("path", type=pathlib.Path, nargs="?", default=None, help="Directory/files to run from.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(args=None if sys.argv[1:] else ['--help'])
    if args.verbose:
        print(f"CLI: {args=}")
    path = args.path.expanduser()

    man = Manager(args.verbose)
    if path.is_file():
        man.analyze(path)
    else:
        for file in path.glob("*.py"):
            if not file.name.startswith("_"):
                man.analyze(file)
    man.summary()
    man.run(dry_run=args.dry_run)
