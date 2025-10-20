import base64
import hashlib
import inspect
import re
import sys
from importlib import util
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import FunctionType, ModuleType


def register(func):
    # TODO: actually add decorator arguments
    setattr(func, "_danta_info", {})
    return func


class Target:

    def __init__(self, func, module, requires: list[str] | None = None):
        self.name: str = func.__name__
        self.func = func
        self.module: ModuleType = module
        self.checksum: str = Target.get_checksum(func)
        self.tracked: bool = hasattr(func, "_danta_info")
        self.spec = inspect.signature(func)
        if requires is None:
            self.requires = []
            for name, arg in self.spec.parameters.items():
                if arg.default == inspect.Parameter.empty:
                    self.requires.append(name)
        else:
            self.requires = requires

    def __hash__(self) -> int:
        return hash(self.name)

    def __repr__(self) -> str:
        out = self.checksum[:10]
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


class Manager:

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.targets: set = set()
        self.modules: dict[str, ModuleType] = {}

    def analyze(self, path: str | Path):
        path = Path(path)
        assert path.exists() and path.is_file() and path.suffix == '.py'
        if self.verbose:
            print("Loading", path)
        # Load in the module
        spec: ModuleSpec | None = util.spec_from_file_location(path.stem, path)
        assert spec is not None, f"Couldn't load the module specs from file {path}"
        dynmod = util.module_from_spec(spec)
        assert spec.loader is not None, f"Couldn't load the module from file {path}"
        spec.loader.exec_module(dynmod)
        self.modules[path.name] = dynmod
        for name, func in dynmod.__dict__.items():
            if not name.startswith("_") and callable(func):
                self.register(func, dynmod)
        return dynmod

    def register(self, func: FunctionType, module: ModuleType):
        name = f"{module.__name__}.{func.__name__}"
        if name in self.targets:
            raise NotImplementedError
        else:
            self.targets.add(Target(func, module))

    def run(self, state={}, dry_run=False):
        runnable = {t for t in self.targets if t.tracked}
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
                args = {k: v for k, v in state.items() if k in i.requires}
                if self.verbose:
                    print(f"{i.name}(**{args})")
                state[i.name] = i.func(**args)


    def summary(self):
        for i in self.targets:
            print(i)


# def main(argv):
#     os.environ.get("")
#     store = ".func_chk.p"
#     assert len(argv) >= 2
#     key = argv[1].strip()
#     mod, func = key.split(":")
#     known = {}
#     if os.path.exists(store):
#         with open(store, 'rb') as f:
#             known = pickle.load(f)
#     check = get_checksum(mod, func, False)
#     if "--set" in argv:
#         known[f"{mod}:{func}"] = check
#         with open(store, 'wb') as f:
#             pickle.dump(known, f)
#     else:
#         if key in known.keys() and known[key] == check:
#             sys.exit(0)
#         sys.exit(1)
