"""Reject remaining PE imports of exact reviewed Qt removal targets."""
import argparse
import json
from pathlib import Path, PurePosixPath


def validate(plan_path, remaining_path):
    plan = json.loads(Path(plan_path).read_text(encoding='utf-8-sig'))
    remaining = json.loads(Path(remaining_path).read_text(encoding='utf-8-sig'))
    removed_paths = {entry['path'] for entry in plan['files']}
    removed = {PurePosixPath(entry['path']).name.casefold()
               for entry in plan['files']
               if PurePosixPath(entry['path']).suffix.casefold() in ('.exe', '.dll', '.pyd')}
    errors = []
    for module in remaining['modules']:
        if module.get('error'):
            errors.append(f"Unparsed PE: {module['path']}: {module['error']}")
        if module['path'] in removed_paths:
            errors.append(f"Removal target remains: {module['path']}")
        for dependency in module['imports'] + module['delayed']:
            if dependency.casefold() in removed:
                errors.append(f"{module['path']} still imports {dependency}")
    if errors:
        raise RuntimeError('\n'.join(errors))
    print(f"Checked {len(remaining['modules'])} remaining PE modules: no imports of reviewed removed modules")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan')
    parser.add_argument('remaining')
    arguments = parser.parse_args()
    validate(arguments.plan, arguments.remaining)
