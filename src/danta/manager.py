import pickle
from pathlib import Path

from .target import TrackedModule


class Manager:

    @property
    def all_targets(self):
        out = set()
        for mod in self.modules:
            out = out.union(mod.functions)
        return out

    @property
    def tracked_targets(self):
        out = set()
        for mod in self.modules:
            out = out.union(mod.functions)
        return out

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.modules: list[TrackedModule] = []
        # TODO: Allow other working dir
        self.cache_dir = Path(".danta_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self.state = {}

    def update(self):
        for mod in self.modules:
            mod.update(self.verbose)
            # if self.module_times[name] > os.stat(
        # i.check_status(self.checksums)
        return

    def add_module(self, path: str | Path):
        path = Path(path)
        mod = TrackedModule(path, self.cache_dir)
        if self.verbose:
            print("Loading", path)
        self.modules.append(mod)

    def run(self, dry_run=False):
        runnable = self.tracked_targets
        ordered = []
        while len(runnable) > 0:
            for f in runnable:
                if f.satisfied(ordered):
                    break
            else:
                raise LookupError(f"Circular or unsatisfied dependencies for {runnable}")
            ordered.append(f)
            runnable.remove(f)
        if dry_run:
            print("Solution:")
            for i in ordered:
                print("    " + str(i)[12:])
        else:
            for i in ordered:
                i.run(self.state, self.verbose)
        # with open(self.cache_state, 'wb') as file:
            # pickle.dump(self.state, file)
        for mod in self.modules:
            mod.write_state()

    def summary(self):
        for m in self.modules:
            print("Module", m.name)
            for f in m.functions:
                print("    ", f)
