"""Run the existing regression witnesses linked to the crypto-bot research catalog."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
CATALOG = ROOT / 'docs/research/crypto-bot-20261115/scenario-catalog.json'


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


class AuditResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = {}

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes[test.id()] = 'PASS'

    def addFailure(self, test, error):
        super().addFailure(test, error)
        self.outcomes[test.id()] = 'FAIL'

    def addError(self, test, error):
        super().addError(test, error)
        self.outcomes[test.id()] = 'ERROR'

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes[test.id()] = 'SKIP'

    def addExpectedFailure(self, test, error):
        super().addExpectedFailure(test, error)
        self.outcomes[test.id()] = 'EXPECTED_FAILURE'

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.outcomes[test.id()] = 'UNEXPECTED_SUCCESS'

    def addSubTest(self, test, subtest, error):
        super().addSubTest(test, subtest, error)
        if error is not None:
            self.outcomes[test.id()] = 'FAIL'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'reports/crypto-bot-research-20261115/capability-audit.json')
    args = parser.parse_args()
    catalog_bytes = CATALOG.read_bytes()
    catalog = json.loads(catalog_bytes)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    rows = []
    selected = set()
    for scenario in catalog['scenarios']:
        row = dict(scenario)
        row['regression_result'] = 'NO_LINKED_REGRESSION'
        row['exchange_acceptance'] = 'NOT_RUN'
        row['witness_test_id'] = None
        row['source_sha256'] = {}
        for source in scenario['source_files']:
            row['source_sha256'][source] = hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
        if scenario['test_method']:
            module = Path(scenario['test_file']).stem
            tests = flatten(loader.loadTestsFromName(module))
            matches = [test for test in tests if test.id().endswith('.' + scenario['test_method'])]
            if len(matches) != 1:
                row['regression_result'] = 'WITNESS_UNRESOLVED'
            else:
                test = matches[0]
                row['witness_test_id'] = test.id()
                if test.id() not in selected:
                    suite.addTest(test)
                    selected.add(test.id())
                row['test_sha256'] = hashlib.sha256((ROOT / scenario['test_file']).read_bytes()).hexdigest()
        rows.append(row)
    result = unittest.TextTestRunner(verbosity=1, resultclass=AuditResult).run(suite)
    for row in rows:
        if row['witness_test_id']:
            row['regression_result'] = result.outcomes.get(row['witness_test_id'], 'NOT_COMPLETED')
    report = dict(schema_version=1, observed_at_utc=datetime.now(timezone.utc).isoformat(),
                  catalog_sha256=hashlib.sha256(catalog_bytes).hexdigest(),
                  scope='Existing isolated regression witnesses. Per-symbol exchange acceptance pending.',
                  scenario_count=len(rows), tests_run=result.testsRun,
                  regression_counts=dict(Counter(row['regression_result'] for row in rows)),
                  scenarios=rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('scenario_count', 'tests_run', 'regression_counts')},
                     ensure_ascii=False))
    print(args.output)
    unresolved = any(row['regression_result'] in ('WITNESS_UNRESOLVED', 'NOT_COMPLETED') for row in rows)
    return 0 if result.wasSuccessful() and not unresolved else 1


if __name__ == '__main__':
    raise SystemExit(main())
