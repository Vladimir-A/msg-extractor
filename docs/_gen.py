"""
Helper script for generating the necessary RST files.
"""

import os
import pathlib

from typing import Dict, List, NamedTuple, Tuple


DIRECTORY = pathlib.Path(__file__).parent


class Package(NamedTuple):
    """
    A class representing one of the subpackages of a module.
    """
    modules: List[str]
    packages: List[str]



def _readProject(root) -> Dict[str, Dict[str, bool]]:
    """
    Searches a project for Python files, using their locations to create a
    dictionary of module paths and their submodules/subpackages. Submodules/subpackages will be a dictionary, where the key is the name and the
    """
    # This whole function could almost certainly be optimized, but I'll worry
    # about that some other time.
    root = pathlib.Path(root)
    rootName = root.name
    ret = {rootName: {}}
    for x in root.glob('**/*.py'):
        # Ignore internal files.
        if x.name.startswith('_'):
            continue

        # Get all parent components.
        parents = []
        parent = x.parent
        while parent != root:
            parents.append(parent.name)
            parent = parent.parent

        # Check if any of the parents start with an underscore. If they do,
        # ignore the current path.
        if any(y.startswith('_') for y in parents):
            continue

        parents.append(rootName)

        parents.reverse()

        # Add the subpackages and submodules.
        for index, name in enumerate(parents[1:]):
            path = '.'.join(parents[:index + 1])
            if path not in ret:
                ret[path] = {}
            if name not in ret[path]:
                ret[path][name] = True
        if (path := '.'.join(parents)) not in ret:
            ret[path] = {}
        ret[path][x.name] = False

    return ret


def _makePackage(name: str, data: Dict[str, bool]) -> Package:
    return Package([f'{name}.{x}' for x in data if not data[x]], [f'{name}.{x}' for x in data if data[x]])


def run():
    for x in getAutoGenerated():
        os.remove(DIRECTORY / x)
    project = readProject(DIRECTORY.parent / 'extract_msg')
    for x, y in project.items():
        generateFile(x, y)

    writeAutoGenerated((x + '.rst' for x in project))


def generateFile(name: str, package: Package):
    with open(DIRECTORY / (name + '.rst'), 'w') as f:
        # Header.
        temp = name.replace('_', '\\_') + ' package'
        f.write(f'{temp}\n{"=" * len(temp)}\n\n')

        # Subpackages.
        if package.packages:
            f.write('Subpackages\n-----------\n\n')
            f.write('.. toctree::\n')
            f.write('   :maxdepth: 4\n\n')
            f.write('   ' + '\n   '.join(package.packages))
            f.write('\n\n')

        # Submodules.
        if package.modules:
            f.write('Submodules\n----------\n\n')
            for module in package.modules:
                if module.endswith('.py'):
                    module = module[:-3]
                temp = module.replace('_', '\\_') + ' module'
                f.write(f'{temp}\n{"-" * len(temp)}\n\n')
                f.write(f'.. automodule:: {module}\n')
                f.write('   :members:\n')
                f.write('   :undoc-members:\n')
                f.write('   :show-inheritance:\n\n')

        # Module contents.
        f.write('Module contents\n---------------\n\n')
        f.write(f'.. automodule:: {name}\n')
        f.write('   :members:\n')
        f.write('   :undoc-members:\n')
        f.write('   :show-inheritance:\n')


def getAutoGenerated() -> List[str]:
    """
    Retrieves the list of previously autogenerated files.
    """
    with open(DIRECTORY / '_autogen.txt', 'r') as f:
        return [x.strip() for x in f if x]


def readProject(root) -> Dict[str, Package]:
    """
    Returns a dictionary of package names to Package instances for a project.
    """
    initialRead = _readProject(root)
    return {x: _makePackage(x, y) for x, y in initialRead.items()}


def writeAutoGenerated(files : List[str]) -> None:
    """
    Writes the _autogen.txt file.
    """
    with open(DIRECTORY / '_autogen.txt', 'w') as f:
        f.write('\n'.join(files))


if __name__ == '__main__':
    run()