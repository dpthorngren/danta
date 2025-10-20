import base64
import pickle
import hashlib
import inspect
import os
import re
import sys
from importlib import reload, util
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import FunctionType, ModuleType


def register(func):
    # TODO: actually add decorator arguments
    setattr(func, "_danta_info", {})
    return func


class TrackedModule:
    @property
    def tracked(self):
        return {f for f in self.functions if f.tracked}

    @property
    def checksums(self):
        return {f.name: f.checksum for f in self.functions}

    def __init__(self, path: Path, cache_dir: Path):
        self.path = path
        self.name = path.stem
        assert path.exists() and path.is_file() and path.suffix == '.py'
        self.time = 0
        self.functions = set()
        self.cache_dir = cache_dir
        self.cache_file = self.cache_dir / f"{self.name}_state.pickle"
        self.state = {}
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'rb') as file:
                    self.state = dict(pickle.load(file))
            except EOFError:
                self.cache_file.unlink()
        self.update()

    def write_state(self):
        for f in self.functions:
            assert not f.changed
        print("SAVING", self.state)
        self.state["_checksums"] = self.checksums
        with open(self.cache_file, 'wb') as file:
            pickle.dump(self.state, file)

    def update(self, verbose=True):
        time = self.path.stat().st_mtime_ns
        if time > self.time:
            if verbose:
                print(f"{self.name} changed, reloading.")
            spec: ModuleSpec | None = util.spec_from_file_location(self.path.stem, self.path)
            assert spec is not None, f"Couldn't load the module specs from file {self.path}"
            self.module = util.module_from_spec(spec)
            assert spec.loader is not None, f"Couldn't load the module from file {self.path}"
            spec.loader.exec_module(self.module)
            sys.modules[self.name] = self.module
            functions = set()
            for n, f in self.module.__dict__.items():
                if not n.startswith("_") and callable(f):
                    functions.add(self.register_function(f))
            # Remove functions no longer referenced
            self.functions = functions
            self.time = self.path.stat().st_mtime_ns
        else:
            if verbose:
                print(f"{self.name} unchanged.")

    def register_function(self, func):
        '''Adds or updates a function target.'''
        target = Target(func, self)
        check = self.checksums[target.name] if target.name in self.checksums.keys() else ""
        target.changed = check == target.checksum
        for f in self.functions:
            if f.name == target.name:
                f.update(target)
                break
        else:
            self.functions.add(target)
        return target


class Target:

    def __init__(self, func: FunctionType, module: TrackedModule, requires: list[str] | None = None):
        assert type(func) is FunctionType
        self.name: str = func.__name__
        self.fullname: str = module.name + "." + self.name
        self.func = func
        self.module = module
        self.checksum: str = Target.get_checksum(func)
        self.tracked: bool = hasattr(func, "_danta_info")
        self.spec = inspect.signature(func)
        self.changed = True
        if requires is None:
            self.requires = []
            for name, arg in self.spec.parameters.items():
                if arg.default == inspect.Parameter.empty:
                    self.requires.append(name)
        else:
            self.requires = requires

    def infiles_changed(self):
        # TODO: Check file dependencies
        return False

    def update(self, target) -> bool:
        assert self.fullname == target.fullname
        if target != self:
            print(self.name, "changed")
            self.changed = self.checksum == target.checksum
            self.func = target.func
            self.module = target.module
            self.checksum = target.checksum
            self.tracked = target.tracked
            self.spec = target.spec
        return self.changed

    def run(self, state, verbose=False):
        if self.fullname in state.keys() and not (self.changed or self.infiles_changed()):
            print(f"Cached {self.name}()")
        else:
            args = {k: state[f"{self.module.name}.{k}"] for k in self.requires}
            # self.module.name +"."+ k: v for k, v in state.items() if k in self.requires}
            if verbose:
                print(f"Called {self.name}(**{args})")
            state[self.fullname] = self.func(**args)
            self.changed = False
        return state[self.fullname]

    def __hash__(self) -> int:
        return hash(self.fullname) + hash(self.checksum) + hash(self.tracked)

    def __repr__(self) -> str:
        out = "[" + self.checksum[:10] + "]"
        out += '* ' if self.tracked else '  '
        out += self.name
        out += "(" + ", ".join(self.requires) + ")"
        return out

    def satisfied(self, available) -> bool:
        for i in self.requires:
            for j in available:
                if i == j.name:
                    break
            else:
                return False
        return True

    @staticmethod
    def get_checksum(func, verbose=False):
        code = inspect.getsource(func)
        if verbose:
            print(code)
        # Remove comments, blank lines, and trailing whitespace
        code = re.sub(r"\s*#.*$", "", code, flags=re.M)
        code = re.sub(r"^(?:[\t ]*(?:\r?\n|\r))+", "", code, flags=re.M)
        code = re.sub(r"\s+$", "", code, flags=re.M)
        code = code.strip()
        if verbose:
            print(code)
        hash = hashlib.shake_128(code.encode("utf-8")).digest(30)
        return base64.b32encode(hash).decode("utf-8")
