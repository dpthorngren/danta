import base64
import hashlib
import inspect
import re
from types import FunctionType


def register(func):
    # TODO: actually add decorator arguments
    setattr(func, "_danta_info", {})
    return func


class _Cache_Empty_:
    pass


def get_checksum(code, verbose=False):
    '''Gets the checksum if the input code, with comments and whitespace removed.'''
    # Remove comments, blank lines, and trailing whitespace
    code = re.sub(r"\s*#.*$", "", code, flags=re.M)
    code = re.sub(r"^(?:[\t ]*(?:\r?\n|\r))+", "", code, flags=re.M)
    code = re.sub(r"\s+$", "", code, flags=re.M)
    code = code.strip()
    if verbose:
        print(code)
    hash = hashlib.shake_128(code.encode("utf-8")).digest(30)
    return base64.b32encode(hash).decode("utf-8")


class TargetFunction:
    '''A function, tracked or not, in a tracked module.  Keeps a cached result if
    available, as well as a code checksum and dependency names to determine if the
    cached value may be used.'''

    def __init__(self, func: FunctionType, module):
        '''For a given function and its parent TrackedModule, build target info.'''
        assert type(func) is FunctionType
        self.name: str = func.__name__
        self.fullname: str = module.name + "." + self.name
        self.func = func
        self.module = module
        self.checksum: str = get_checksum(inspect.getsource(func))
        self.output = _Cache_Empty_
        self.tracked: bool = hasattr(func, "_danta_info")
        self.changed = False
        self.requires = []
        spec = inspect.signature(func)
        for name, arg in spec.parameters.items():
            if arg.default == inspect.Parameter.empty:
                self.requires.append(f"{self.module.name}.{name}")

    def infiles_changed(self):
        # TODO: Check file dependencies
        return False

    def run(self, all_targets, force=False, verbose=True):
        '''Run the function if the cache is out of date using data from all_targets,
        which is a dict of other TargetFunctions, indexed by name.'''
        must_run = force or self.output is _Cache_Empty_ or self.infiles_changed()
        args = {}
        for req_name in self.requires:
            req = all_targets[req_name]
            must_run |= req.changed
            args[req.name] = req.output
        if must_run:
            if verbose:
                print(f"Called {self.name}(", end="")
                print(", ".join([f"{k} = {v}" for k, v in args.items()]), end="")
                print(")")
            self.output = self.func(**args)
            self.changed = True
        else:
            if verbose:
                print(f"Cache used for {self.name}")
            self.changed = False
        return self.output

    def __repr__(self) -> str:
        out = "[" + self.checksum[:10] + "]"
        out += '* ' if self.tracked else '  '
        out += self.name
        out += "(" + ", ".join(self.requires) + ")"
        return out

    def satisfied(self, available) -> bool:
        '''Reports whether all dependencies are in "available", which is an iterable
        of TargetFunctions.'''
        for i in self.requires:
            for j in available:
                if i == j.fullname:
                    return i
                    break
            else:
                return False
        return True
