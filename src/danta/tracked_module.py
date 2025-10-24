import pickle
from importlib import util
from pathlib import Path

from .target import TargetFunction, _Cache_Empty_


class TrackedModule:
    '''A wrapper for a module that tracks the functions defined therein
    and can detect if each individually has changed, as well as read
    and write their outputs and checksums to a collective cache file.'''

    @property
    def tracked_functions(self):
        return [f for f in self.functions if f.tracked]

    def __init__(self, path: Path, cache_dir: Path, verbose=False):
        self.path = path
        self.name = path.stem
        self.verbose = verbose
        assert path.exists() and path.is_file() and path.suffix == '.py'
        self.functions = []
        self.file_cache = cache_dir / f"{self.name}_state.pickle"
        self.read_state()
        self.update()

    def read_state(self):
        '''Writes all function outputs and their corresponding checksums
        to {self.name}_state.pickle'''
        self.cache = {}
        self.checksums = {}
        if self.file_cache.exists():
            try:
                with open(self.file_cache, 'rb') as file:
                    self.cache = dict(pickle.load(file))
                    if "_checksums" in self.cache.keys():
                        self.checksums = self.cache.pop('_checksums')
            except EOFError:
                self.file_cache.unlink()

    def write_state(self):
        '''Reads the cache of function outputs and checksums stored in 
        {self.name}_state.pickle to be used by the functions if the
        code checksums match and inputs haven't changed.'''
        self.cache = {}
        self.checksums = {}
        for f in self.tracked_functions:
            if f.output == _Cache_Empty_:
                continue
            self.cache[f.name] = f.output
            self.checksums[f.name] = f.checksum
        if self.verbose:
            print("Saving", self.name, "cache", list(self.cache.keys()))
        self.cache["_checksums"] = self.checksums
        with open(self.file_cache, 'wb') as file:
            pickle.dump(self.cache, file)
        del self.cache['_checksums']

    def update(self):
        '''Reload the module source file, import it, and replace the
        functions objects.'''
        spec = util.spec_from_file_location(self.path.stem, self.path)
        assert spec is not None, f"Couldn't load the module specs from file {self.path}"
        self.module = util.module_from_spec(spec)
        assert spec.loader is not None, f"Couldn't load the module from file {self.path}"
        spec.loader.exec_module(self.module)
        self.functions = []
        for n, f in self.module.__dict__.items():
            if n.startswith("_") or not callable(f):
                continue
            func = TargetFunction(f, self)
            if func.tracked and self.checksums.get(func.name, "") == func.checksum:
                func.output = self.cache[func.name]
            self.functions.append(func)
