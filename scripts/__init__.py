"""Repository development and validation commands."""
from pathlib import Path

def script_path(name):
    """Find a command by basename across the explicit script domains."""
    if Path(name).name != name:
        raise ValueError('Expected a script basename')
    candidates = [Path(__file__).parent / domain / name
                  for domain in ('bot', 'chart', 'integration', 'maintenance')]
    matches = [candidate for candidate in candidates if candidate.is_file()]
    if len(matches) != 1:
        raise ValueError(f'Script must resolve uniquely: {name}')
    return matches[0]
