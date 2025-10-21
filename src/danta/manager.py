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
            out = out.union(mod.tracked)
        return out

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.modules: list[TrackedModule] = []
        # TODO: Allow other working dir
        self.cache_dir = Path(".danta_cache")
        self.cache_dir.mkdir(exist_ok=True)

    def add_module(self, path: str | Path):
        path = Path(path)
        mod = TrackedModule(path, self.cache_dir)
        if self.verbose:
            print("Loading", path)
        self.modules.append(mod)

    def update(self):
        for mod in self.modules:
            mod.update(self.verbose)

    def _recursive_changed(self, target, all_targets):
        target.changed = True
        if target.name in all_targets.keys():
            all_targets.pop(target.name)
        for t in target.requires:
            if t in all_targets.keys():
                self._recursive_changed(all_targets[t], all_targets)

    def run(self, dry_run=False):
        all_targets = {t.name: t for t in self.all_targets}
        while len(all_targets) > 0:
            for t in all_targets.values():
                if t.changed:
                    self._recursive_changed(t, all_targets)
                    break
            else:
                break
        state = {m.name: m.state for m in self.modules}
        runnable = self.all_targets
        ordered = []
        while len(runnable) > 0:
            for f in runnable:
                if not f.tracked:
                    f.changed = False
                    break
                elif f.satisfied(ordered):
                    break
            else:
                raise LookupError(f"Circular or unsatisfied dependencies for {runnable}")
            if f.tracked:
                ordered.append(f)
            runnable.remove(f)
        if self.verbose:
            print("Solution:")
            for i in ordered:
                print("    " + str(i)[14:])
        if dry_run:
            return
        for i in ordered:
            i.run(state, self.verbose)
        for mod in self.modules:
            mod.write_state()

    def summary(self):
        for m in self.modules:
            print("Module", m.name)
            for f in m.functions:
                print("   ", f)
