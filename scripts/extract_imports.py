import ast
from dataclasses import dataclass
from typing import Generator, List, Union


@dataclass
class Import:
    """A simple dataclass for imports. It's probably better to use ast.Import and ast.ImportFrom."""

    module: str
    """The imported module. With leading dots for relative imports."""
    symbols: List[str]
    """Symbols imported from the module with from-imports."""

    def __str__(self):
        if not self.symbols:
            return self.module
        elif len(self.symbols) == 1:
            return f"{self.module}.{self.symbols[0]}"
        else:
            return f'{self.module}.({", ".join(self.symbols)})'


def extract_imports(root: ast.AST) -> Generator[Import, None, None]:
    """Extracts all imports contained in an AST node."""

    for node in ast.walk(root):
        if isinstance(node, ast.Import):
            for name in clear_aliases(node.names):
                yield Import(name, [])
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            yield Import(f"{prefix}{node.module}", list(clear_aliases(node.names)))


def clear_aliases(names: List[Union[str, ast.alias]]) -> Generator[str, None, None]:
    """Changes all aliases in a 'node.names' list to their original names."""

    for name in names:
        if isinstance(name, str):
            yield name
        elif isinstance(name, ast.alias):
            yield name.name
