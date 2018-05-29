#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 07. Mar 2018, Tobias Kohn
# 20. Mar 2018, Tobias Kohn
#
from .ppl_ast import *

def union(items):
    if len(items) == 1:
        return items[0][1]

    if len(items) == 2:
        tests = [i[0] for i in items]
        values = [i[1] for i in items]
        if values[0] == values[1]:
            return values[0]
        if tests[0] is None or is_boolean_true(tests[0]) or \
                (isinstance(tests[0], AstUnary) and not isinstance(tests[1], AstUnary)):
            tests[0], tests[1] = tests[1], tests[0]
            values[0], values[1] = values[1], values[0]

        if is_negation_of(tests[0], tests[1]):
            return makeIf(tests[0], values[0], values[1])

    raise RuntimeError("cannot take the union of '{}'".format(items))


class BranchScope(object):

    def __init__(self, *, parent=None, names=None, condition:Optional[AstNode]=None):
        self.condition = condition
        self.parent = parent
        self.branches = []
        self.current_branch = self      # type:BranchScope
        if names is not None:
            self.values = { key: None for key in names }
        else:
            self.values = {  }

    def new_branching(self, cond:AstNode):
        result = BranchScope(parent=self.current_branch, condition=cond)
        self.current_branch.branches = [result]
        self.current_branch = result
        return result

    def switch_branch(self):
        self.current_branch = self.current_branch.parent
        cond = AstUnary('not', self.current_branch.branches[-1].condition)
        result = BranchScope(parent=self.current_branch, condition=cond)
        self.current_branch.branches.append(result)
        self.current_branch = result
        return result

    def end_branching(self):
        self.current_branch = self.current_branch.parent
        branch = self.current_branch
        names = set()
        for b in branch.branches:
            names = set.union(names, b.names)
        values = { key: [] for key in names }
        for key in names:
            if not all([key in b.values for b in branch.branches]):
                values[key].append((None, branch[key]))
        for b in branch.branches:
            for key in b.values:
                values[key].append((b.condition, b.values[key]))
        for key in values:
            self.values[key] = union(values[key])
        branch.branches = []
        return branch

    def get_value(self, name:str):
        assert type(name) is str
        if name in self.values:
            return self.values[name]
        elif isinstance(self.parent, BranchScope):
            return self.parent.get_value(name)
        elif isinstance(self.parent, BranchScopeVisitor):
            return self.parent.branch.get_value(name)
        else:
            return None

    def set_value(self, name:str, value):
        assert type(name) is str
        self.values[name] = value

    def __getitem__(self, item):
        if type(item) is str:
            return self.get_value(item)
        else:
            raise TypeError("key must be of type 'str', not '{}'".format(type(item)))

    def __setitem__(self, key, value):
        if type(key) is str:
            return self.set_value(key, value)
        else:
            raise TypeError("key must be of type 'str', not '{}'".format(type(key)))

    @property
    def names(self):
        return set(self.values.keys())


class BranchScopeContext(object):
    """
    The `BranchScopeContext` is a thin layer used to support scoping in `with`-statements inside methods of
    `BranchScopedVisitor`, i.e. `with create_scope(): do something`.
    """

    def __init__(self, visitor):
        self.visitor = visitor

    def __enter__(self):
        return self.visitor.branch

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.visitor.leave_scope()


class LockScope(object):

    def __init__(self, prev=None):
        self.prev = prev
        self.names = set()
        self.write_names = set()
        assert prev is None or isinstance(prev, LockScope)

    def lock(self, name:str):
        if type(name) is str and name != '_' and name != '':
            self.names.add(name)

    def lock_write(self, name:str):
        if type(name) is str and name != '_' and name != '':
            self.write_names.add(name)

    def unlock(self, name:str):
        if name in self.names:
            self.names.remove(name)
        if name in self.write_names:
            self.write_names.remove(name)

    def is_locked(self, name:str):
        if name in self.names or name in self.write_names:
            return True
        elif self.prev is not None:
            return self.prev.is_locked(name)
        else:
            return False

    def is_write_locked(self, name:str):
        if name in self.write_names:
            return True
        elif self.prev is not None:
            return self.prev.is_locked(name)
        else:
            return False


class NameLockContext(object):

    def __init__(self, visitor):
        self.visitor = visitor

    def __enter__(self):
        return self.visitor.name_lock

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.visitor.leave_name_lock()


class BranchScopeVisitor(Visitor):

    def __init__(self, symbols:list):
        self.branch = BranchScope(names=symbols)
        self.symbols = symbols
        self.name_lock = LockScope()

    def enter_scope(self, condition:AstNode):
        self.branch.new_branching(condition)

    def leave_scope(self):
        self.branch.end_branching()

    def enter_name_lock(self):
        self.name_lock = LockScope(self.name_lock)

    def leave_name_lock(self):
        self.name_lock = self.name_lock.prev
        assert isinstance(self.name_lock, LockScope)

    def create_scope(self, condition:AstNode):
        self.enter_scope(condition)
        return BranchScopeContext(self)

    def create_lock(self, *names):
        self.enter_name_lock()
        for n in names:
            self.name_lock.lock(n)
        return NameLockContext(self)

    def create_write_lock(self):
        self.enter_name_lock()
        self.lock_all_write()
        return NameLockContext(self)

    def switch_branch(self):
        self.branch.switch_branch()

    def define(self, name:str, value):
        if self.name_lock.is_write_locked(name):
            self.name_lock.lock(name)
        else:
            self.branch[name] = value

    def define_all(self, names:list, values:list, *, vararg:Optional[str]=None):
        assert type(names) is list
        assert type(values) is list
        assert vararg is None or type(vararg) is str
        for name, value in zip(names, values):
            if isinstance(name, AstSymbol):
                name = name.name
            if type(name) is str:
                self.define(name, value)
        if vararg is not None:
            self.define(str(vararg), makeVector(values[len(names):]) if len(values) > len(names) else [])

    def resolve(self, name:str):
        if not self.name_lock.is_locked(name):
            return self.branch[name]
        else:
            return None

    def lock_all(self):
        for symbol in self.symbols:
            self.name_lock.lock(symbol.full_name)

    def lock_all_write(self):
        for symbol in self.symbols:
            self.name_lock.lock_write(symbol.full_name)

    def lock_name(self, name:str):
        self.name_lock.lock(name)

    def unlock_name(self, name:str):
        self.name_lock.unlock(name)

    def lock_name_write(self, name:str):
        self.name_lock.lock_write(name)

    def is_constant(self, name:str):
        for sym in self.symbols:
            if sym.name == name:
                return sym.read_only or sym.modify_count == 0
        return False

    def get_usage_count(self, name:str):
        for sym in self.symbols:
            if sym.name == name:
                return sym.usage_count
        return None
