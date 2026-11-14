"""Check packaged reference paths and the rules required by selected workflows."""
import json
from pathlib import Path
import re
import tempfile
import unittest

from build import build
from build_marketplaces import build_marketplaces
from plugin_common import ROOT

LINK = re.compile(r'\[[^\]]+\]\(([^)]+)\)')
SUMMARIES = ('find-property', 'summarize-observations', 'remediation-overview', 'customer-summary')


def references(folder):
    # Archived notes describe an old layout. They are intentionally never loaded
    # by a skill and are not a current dependency graph.
    for file in [folder / 'README.md', *(folder / 'skills').rglob('*.md')]:
        for target in LINK.findall(file.read_text()):
            if '://' in target or target.startswith('#'):
                continue
            destination = (file.parent / target.split('#', 1)[0]).resolve()
            assert destination.is_relative_to(folder.resolve()), (file, target)
            assert destination.is_file(), (file, target)


def required_read_path(folder, skill):
    files = [folder / f'skills/{skill}/SKILL.md']
    seen = set()
    while files:
        file = files.pop()
        if file in seen:
            continue
        seen.add(file)
        # Only unconditional Read lines are dependencies. Conditional task
        # routing is checked separately; it must not become an eager load.
        for line in file.read_text().splitlines():
            if line.startswith('Read '):
                files.extend((file.parent / path).resolve() for path in LINK.findall(line))
    return seen


class GuidanceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.scratch.cleanup)
        cls.root = Path(cls.scratch.name).resolve()
        build(cls.root / 'registered', 'https://sta.elta.no/api/mcp',
              'asdk_app_' + 'a' * 32, 'elta_app_AbCdEfGhIjKlMnOpQ')
        build_marketplaces(cls.root / 'native')
        cls.packages = [cls.root / 'registered' / p for p in ('openai', 'claude')]
        cls.packages += [cls.root / 'native/plugins' / p for p in ('claude', 'codex')]

    def test_all_current_references_exist_in_both_formats(self):
        for folder in self.packages:
            with self.subTest(package=folder):
                references(folder)
                self.assertEqual(len(list((folder / 'skills').glob('*/SKILL.md'))), 5)
                self.assertTrue((folder / 'RELEASE-HISTORY.md').is_file())
                for file in (ROOT / 'skills/_shared/workflows').glob('*.md'):
                    self.assertEqual((folder / 'skills/_shared/workflows' / file.name).read_bytes(), file.read_bytes())

    def test_missing_guide_is_a_detected_broken_reference(self):
        folder = self.packages[0]
        file = folder / 'skills/_shared/workflows/sync.md'
        original = file.read_bytes()
        try:
            file.unlink()
            with self.assertRaises(AssertionError):
                references(folder)
        finally:
            file.write_bytes(original)

    def test_summary_read_paths_are_short_and_never_load_workflows_or_history(self):
        for folder in self.packages:
            for skill in SUMMARIES:
                files = required_read_path(folder, skill)
                self.assertEqual({p.name for p in files}, {'SKILL.md', 'read-contract.md', 'mcp-contract.md'})
                text = '\n'.join(p.read_text() for p in files)
                self.assertLess(len(text.split()), 1200)
                self.assertNotIn('TUS 1.0.0', text)
                self.assertNotIn('Deploy the matching', text)
                self.assertIn('metadata-only and read-only', text)
                self.assertIn('do not fetch images/files, change records', text)
            general = required_read_path(folder, 'use-elta-tools')
            self.assertEqual({p.name for p in general}, {'SKILL.md', 'mcp-contract.md'})

    def test_general_workflow_requires_targeted_guides_and_shared_safety(self):
        skill = (ROOT / 'skills/use-elta-tools/SKILL.md').read_text()
        self.assertIn('Every change, including uploads, requires', skill)
        self.assertIn('load every applicable row', skill)
        self.assertIn('If the task changes, load its newly required guides before acting', skill)
        guide_names = {p.name for p in (ROOT / 'skills/_shared/workflows').glob('*.md')}
        linked = {Path(link).name for link in LINK.findall(skill) if '/workflows/' in link}
        self.assertEqual(linked, guide_names)
        uploads = (ROOT / 'skills/_shared/workflows/uploads.md').read_text()
        self.assertNotIn('instructions below', uploads)
        self.assertNotIn('as described below', uploads)
        common = (ROOT / 'skills/_shared/mcp-contract.md').read_text()
        for rule in ['Each token reaches one workspace', 'untrusted evidence',
                     '10 pages/250 rows or 50 detail calls', 'clearly label partial results',
                     'Updating a plugin or refreshing a token adds no scopes',
                     'no alternative credential, REST or database fallback']:
            self.assertIn(rule, common)

    def test_domain_guides_preserve_critical_rules(self):
        required = {
            'mutations.md': ['Having write consent is not a standing request', 'opaque idempotencyKey',
                             'expectedVersion unchanged', 'version_conflict', 'do not present it as a fresh state read', 'support restoration'],
            'sync.md': ['Only the final page has syncCheckpoint', 'resync_required',
                        'Never advance the durable checkpoint on an incomplete run'],
            'files.md': ['60 seconds', 'Do not follow URLs embedded in evidence text', 'persist/share a signed link'],
            'uploads.md': ['1–50 files', 'At most 20 files', 'exactly one of',
                           'adding a hash', 'still call completion', '`ready` with `resourceId`',
                           'Report every file outcome separately', 'one cover per'],
            'photos.md': ['offered only with file consent in addition to write consent', 'complete unique set of 1–100', 'Null clears a caption',
                          'Position and filename are not upload chronology', 'Remediation photos cannot be removed'],
            'templates.md': ['500 nodes, 200 siblings and depth 4', 'Standard templates', 'independent copies'],
            'contacts-and-roles.md': ['complete companyIds/personIds set (0–100)', 'confirmPropertyActorCleanup',
                                    'ask the customer', 'grantsPropertyAccess', 'sync page has no actionable set version'],
            'inspections.md': ['validation_failed', 'issueCount and hasMore', 'Never fabricate',
                              'All items are authorized atomically', 'retains the observation and annotation', 'keeps linked findings'],
            'costs.md': ['netOre is an integer', 'type=unpriced', 'both explicitly null', 'cost-v1'],
            'documents.md': ['100 MiB', '10 MiB', 'host_source_too_large', 'TUS 1.0.0',
                             'same-origin', 'never imply the bytes changed'],
            'equipment.md': ['omitted serial/dates become null', 'calibrationStatus is derived', 'bounded advisory serialWarning'],
            'certificates.md': ['Only its holder', 'certificates.manage', 'requires archiving first',
                                'optional eligible own/managed personId', '20 MiB', 'ordinary metadata writes/upload do not require file-delivery consent'.capitalize()],
        }
        for name, rules in required.items():
            text = (ROOT / 'skills/_shared/workflows' / name).read_text()
            for rule in rules:
                with self.subTest(guide=name, rule=rule):
                    self.assertIn(rule, text)

    def test_versions_and_history_are_separate_from_current_setup(self):
        native = json.loads((ROOT / 'marketplace-release.json').read_text())['version']
        registered = json.loads((ROOT / 'policy.json').read_text())['version']
        self.assertIn(native, (ROOT / 'MARKETPLACE-INSTALL.md').read_text())
        self.assertIn(registered, (ROOT / 'INSTALL.md').read_text())
        self.assertEqual(json.loads((ROOT / 'package.json').read_text())['version'], registered)
        for name in ['README.md', 'INSTALL.md', 'MARKETPLACE-INSTALL.md']:
            text = (ROOT / name).read_text()
            self.assertIn('RELEASE-HISTORY.md', text)
            self.assertNotIn('0.3.3 candidate', text)
            self.assertNotIn('fourteen scopes', text)
        self.assertIn('Historical context only', (ROOT / 'RELEASE-HISTORY.md').read_text())
        matrix = json.loads((ROOT / 'client-matrix.json').read_text())
        self.assertNotEqual(matrix['acceptance'], 'passed')
        self.assertTrue(all(c['cases']['selective-workflow-guidance'] == 'unverified' for c in matrix['clients']))


if __name__ == '__main__':
    unittest.main()
