"""D036 startup repair: adapt display literals only in Progress.__init__.

The original frozen diagnostic and all statistical formulas are reused.
The failed V1 did not create a STATE run directory or read ledger arrays.
"""
from scripts.investment import public_pair_diagnostics as base

BASE_SHA = '7cac018b7d98b428211b8bee7e6b012df24854b5fa84c7e312b96540da7cce6b'


def progress_class(digest):
    source = base.ROOT / base.PROGRESS_SOURCE
    base.require(base.sha(source) == digest, 'Pinned original Progress class')
    nodes = [n for n in base.ast.parse(source.read_text()).body
             if isinstance(n, base.ast.ClassDef) and n.name == 'Progress']
    base.require(len(nodes) == 1, 'One original Progress class')
    original = base.hashlib.sha256(base.ast.dump(nodes[0], include_attributes=False).encode()).hexdigest()
    initializers = [n for n in nodes[0].body
                    if isinstance(n, base.ast.FunctionDef) and n.name == '__init__']
    base.require(len(initializers) == 1, 'One original initialization method')
    changes = []
    for node in base.ast.walk(initializers[0]):
        if isinstance(node, base.ast.Dict):
            for index, key in enumerate(node.keys):
                if isinstance(key, base.ast.Constant) and key.value in ('total', 'detail'):
                    base.require(isinstance(node.values[index], base.ast.Constant), 'Only initializer literals')
                    node.values[index] = base.ast.Constant(value=12 if key.value == 'total'
                        else '已接受公开策略账本互补性诊断；不是新组合账户或APR')
                    changes.append(key.value)
    base.require(sorted(changes) == ['detail', 'total'], 'Two display literals, unchanged update method')
    base.ast.fix_missing_locations(nodes[0])
    namespace = {name: getattr(base, name) for name in ('os', 'Path', 'STATE', 'json', 'threading', 'time')}
    exec(compile(base.ast.Module(nodes, type_ignores=[]), str(source) + '<initializer-display-only>', 'exec'), namespace)
    derived = base.hashlib.sha256(base.ast.dump(nodes[0], include_attributes=False).encode()).hexdigest()
    return namespace['Progress'], original, derived


if __name__ == '__main__':
    base.require(base.sha(base.__file__) == BASE_SHA, 'Exact frozen original scientific implementation')
    base.progress_class = progress_class
    base.__file__ = __file__
    base.main()
