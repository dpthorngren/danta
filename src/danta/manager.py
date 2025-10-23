from pathlib import Path

from .tracked_module import TrackedModule


class Manager:
    '''Manages one or more modules to run registered functions from.'''

    @property
    def targets(self):
        return {t.fullname: t for mod in self.modules for t in mod.tracked_functions}

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.modules: list[TrackedModule] = []
        # TODO: Allow other working dir
        self.cache_dir = Path(".danta_cache")
        self.cache_dir.mkdir(exist_ok=True)

    def add_module(self, path: str | Path):
        '''Load a module by its source path and process it to be tracked and run.'''
        path = Path(path)
        if self.verbose:
            print("Loading", path, end=' ')
        mod = TrackedModule(path, self.cache_dir, self.verbose)
        self.modules.append(mod)

    def update(self):
        '''Update all modules and their functions recursively.'''
        for mod in self.modules:
            mod.update()

    def run(self, dry_run=False):
        '''Run all tracked functions, solving the dependency graph and using
        cached values if possible.'''
        # Solve the dependency graph
        runnable = list(self.targets.values())
        ordered = []
        while len(runnable) > 0:
            for f in runnable:
                if f.satisfied(ordered):
                    break
            else:
                # TODO: Try to identify the specific issue
                names = [f.fullname for f in runnable]
                raise LookupError(f"Circular or unsatisfied dependencies for {names}")
            ordered.append(f)
            runnable.remove(f)
        # Report or run the solution
        if dry_run:
            print("Solution:")
            for i in ordered:
                print("    " + str(i)[14:])
            return
        targets = self.targets
        for i in ordered:
            i.run(targets, False, self.verbose)
        for mod in self.modules:
            mod.write_state()
            print(mod.name)
            for f in mod.functions:
                if f.tracked:
                    print(f"    {f.fullname:20} {f.output}")

    def summary(self):
        '''List tracked modules, their functions, and their functions' dependencies.'''
        for m in self.modules:
            print("Module", m.name)
            for f in m.functions:
                print("   ", f)
