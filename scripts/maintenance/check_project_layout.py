"""Validate local imports, document links, move manifest and script dispatch offline."""
import ast
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import script_path


def main():
    errors = []
    counts = dict(python_files=0, local_imports=0, document_links=0, moved_files=0)
    mapping = json.loads((ROOT / 'docs/project/REORGANIZATION-MAP.json').read_text(encoding='utf-8'))
    for old, new in mapping.items():
        counts['moved_files'] += 1
        if not (ROOT / new).is_file():
            errors.append(f'Missing move destination: {new}')
        if old != 'README.md' and (ROOT / old).is_file():
            errors.append(f'Obsolete duplicate: {old}')
    for base in ('agentrader', 'scripts', 'tests'):
        for path in sorted((ROOT / base).rglob('*.py')):
            if '__pycache__' in path.parts:
                continue
            counts['python_files'] += 1
            rel = path.relative_to(ROOT)
            package = '.'.join(rel.parts[:-1])
            try:
                tree = ast.parse(path.read_text(encoding='utf-8-sig'))
            except SyntaxError as exc:
                errors.append(f'{rel}: {exc}')
                continue
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    name = node.module or ''
                    if node.level:
                        name = importlib.util.resolve_name('.' * node.level + name, package)
                    names = [name]
                for name in names:
                    if name.split('.')[0] not in ('agentrader', 'scripts'):
                        continue
                    counts['local_imports'] += 1
                    target = ROOT.joinpath(*name.split('.'))
                    if not target.with_suffix('.py').is_file() and not (target / '__init__.py').is_file():
                        errors.append(f'{rel}:{node.lineno}: unresolved {name}')
    for path in [ROOT / 'README.md', *(ROOT / 'docs').rglob('*.md')]:
        for match in re.finditer(r'!?\[[^\]\n]*\]\(([^\s)]+)\)', path.read_text(encoding='utf-8-sig')):
            url = match[1].split('#')[0]
            if not url or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', url):
                continue
            counts['document_links'] += 1
            if not (path.parent / unquote(url)).exists():
                errors.append(f'{path.relative_to(ROOT)}: missing link {url}')
    # Validate every command used by the dynamic browser dispatcher without launching it.
    from scripts.chart.run_chart_acceptance_packages import PACKAGES
    for entries in PACKAGES.values():
        for entry in entries:
            try:
                script_path(entry[1])
            except ValueError as exc:
                errors.append(str(exc))
    result = dict(passed=not errors, counts=counts, errors=errors)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
