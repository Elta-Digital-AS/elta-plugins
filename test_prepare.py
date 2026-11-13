import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from plugin_common import ROOT, catalog_digest, json_bytes
from prepare import MIRROR_FILES, prepare


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*')
            if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts}


class PrepareTest(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name).resolve()
        self.source = self.root / 'source'
        shutil.copytree(ROOT, self.source, ignore=shutil.ignore_patterns('.git', '__pycache__', 'dist'))
        self.mirror = self.root / 'mirror'
        self.catalog = self.root / 'catalog.json'
        shutil.copy2(self.source / 'mcp-catalog.json', self.catalog)

    def run_prepare(self, check=False):
        return prepare(self.catalog, self.mirror, self.source, check)

    def change_catalog(self):
        catalog = json.loads(self.catalog.read_text())
        added = copy.deepcopy(catalog['tools'][0])
        added.update(name='synthetic_read', operationId='syntheticRead')
        catalog['tools'].append(added)
        self.catalog.write_bytes(json_bytes(catalog))
        return catalog

    def test_repeat_is_idempotent_and_check_is_read_only(self):
        self.assertGreater(self.run_prepare(), 0)
        before = snapshot(self.root)
        self.assertEqual(self.run_prepare(), 0)
        self.assertEqual(self.run_prepare(check=True), 0)
        self.assertEqual(snapshot(self.root), before)
        self.assertFalse((self.source / 'acceptance-history').exists())

    def test_standalone_check_changes_neither_files_nor_mtimes(self):
        self.run_prepare()
        before = {str(p): (p.stat().st_mtime_ns, p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        result = subprocess.run([sys.executable, str(self.source / 'prepare.py'),
                                 '--catalog', str(self.catalog), '--mirror', str(self.mirror), '--check'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        after = {str(p): (p.stat().st_mtime_ns, p.read_bytes()) for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_target_and_changed_or_removed_tools_invalidate_acceptance(self):
        catalog = json.loads(self.catalog.read_text())
        catalog['tools'].pop(0)
        catalog['tools'][0]['file'] = not catalog['tools'][0]['file']
        self.catalog.write_bytes(json_bytes(catalog))
        release_path = self.source / 'marketplace-release.json'
        release = json.loads(release_path.read_text())
        release['resource'] = 'https://example.test/api/mcp'
        release_path.write_bytes(json_bytes(release))
        self.run_prepare()
        matrix = json.loads((self.source / 'client-matrix.json').read_text())
        self.assertEqual(matrix['target'], release['resource'])
        self.assertEqual(matrix['acceptance'], 'unverified')
        self.assertEqual(set(matrix['clients'][0]['tools']), {t['name'] for t in catalog['tools']})
        self.run_prepare(check=True)

    def test_drift_fails_without_writes_and_prepare_repairs(self):
        self.run_prepare()
        for root, name in [(self.source, 'policy.json'), (self.mirror, 'build.py'),
                           (self.source, 'plugins/codex/connection.json')]:
            with self.subTest(name=name):
                path = root / name
                if name == 'policy.json':
                    value = json.loads(path.read_text());value['catalogSha256'] = '0' * 64
                    path.write_bytes(json_bytes(value))
                else:
                    path.write_text('drift')
                before = snapshot(self.root)
                with self.assertRaisesRegex(ValueError, 'PLUGIN_PREPARE_DRIFT'):
                    self.run_prepare(check=True)
                self.assertEqual(snapshot(self.root), before)
                self.assertGreater(self.run_prepare(), 0)
                self.run_prepare(check=True)

    def test_catalog_change_preserves_exact_evidence_and_invalidates_passes(self):
        matrix_path = self.source / 'client-matrix.json'
        matrix = json.loads(matrix_path.read_text())
        matrix['acceptance'] = 'passed'
        for client in matrix['clients']:
            client.update(status='passed', version='synthetic-1', recordedOn='2026-11-13',
                          evidence=['synthetic receipt'], blocker=None,
                          testedConnection={'resource': matrix['target'], 'publicClient': 'fixture'})
            client['tools'] = dict.fromkeys(client['tools'], 'passed')
            client['cases'] = dict.fromkeys(client['cases'], 'passed')
        old_bytes = json_bytes(matrix)
        matrix_path.write_bytes(old_bytes)
        self.run_prepare()
        self.assertEqual(matrix_path.read_bytes(), old_bytes)
        self.assertFalse((self.source / 'acceptance-history').exists())
        catalog = self.change_catalog()
        before = snapshot(self.root)
        with self.assertRaisesRegex(ValueError, 'PLUGIN_PREPARE_DRIFT'):
            self.run_prepare(check=True)
        self.assertEqual(snapshot(self.root), before)
        self.run_prepare()
        history = [p for p in (self.source / 'acceptance-history').glob('*.json') if not p.name.endswith('.release.json')]
        self.assertEqual(len(history), 1)
        self.assertEqual(len(list((self.source / 'acceptance-history').glob('*.release.json'))), 1)
        self.assertTrue(json.loads((self.source / 'marketplace-release.json').read_text())['fullCatalogAcceptance'].startswith('unverified'))
        self.assertEqual(history[0].read_bytes(), old_bytes)
        current = json.loads(matrix_path.read_text())
        self.assertEqual(current['catalogSha256'], catalog_digest(catalog))
        self.assertEqual(current['acceptance'], 'unverified')
        for client in current['clients']:
            self.assertEqual(set(client['tools'].values()), {'unverified'})
            self.assertEqual(set(client['cases'].values()), {'unverified'})
            self.assertEqual(set(client['tools']), {t['name'] for t in catalog['tools']})
            self.assertIsNone(client['testedConnection'])
        self.assertEqual(self.run_prepare(), 0)
        self.assertEqual(history[0].read_bytes(), old_bytes)

    def test_scope_changes_regenerate_full_profile_but_preserve_read_profile(self):
        value = json.loads(self.catalog.read_text())
        value['scopes'].append('synthetic:write');value['scopeClasses']['synthetic:write'] = 'write'
        tool = copy.deepcopy(value['tools'][0]);tool.update(name='synthetic_write',operationId='syntheticWrite',method='POST',write=True,scopes=['synthetic:write'])
        value['tools'].append(tool);self.catalog.write_bytes(json_bytes(value))
        self.run_prepare()
        release_path = self.source / 'marketplace-release.json'
        release = json.loads(release_path.read_text())
        self.assertEqual(release['scopes'], value['scopes'])
        release.update(profile='read-compatible',scopes=['properties:read'])
        release_path.write_bytes(json_bytes(release))
        self.run_prepare()
        self.assertEqual(json.loads(release_path.read_text())['scopes'], ['properties:read'])

    def test_malformed_catalog_matrix_and_secret_refuse_before_writing(self):
        for name, replacement in [('catalog.json', b'{}'), ('source/client-matrix.json', b'[]'),
                                   ('source/INSTALL.md', ('Bearer ' + 'x' * 30).encode())]:
            path = self.root / name;original = path.read_bytes();path.write_bytes(replacement)
            before = snapshot(self.root)
            with self.subTest(name=name), self.assertRaises((ValueError, KeyError, TypeError)):
                self.run_prepare()
            self.assertEqual(snapshot(self.root), before)
            path.write_bytes(original)

    def test_symlink_destination_and_source_refused_before_any_write(self):
        self.run_prepare()
        for path in [self.mirror / 'build.py', self.source / 'skills/_shared/mcp-contract.md',
                     self.source / 'plugins/codex/README.md']:
            original = path.read_bytes();path.unlink()
            outside = self.root / 'outside';outside.write_bytes(original);path.symlink_to(outside)
            before = snapshot(self.root)
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'PLUGIN_SOURCE_ESCAPE'):
                self.run_prepare()
            self.assertEqual(snapshot(self.root), before)
            path.unlink();path.write_bytes(original)

    def test_overlap_refused_and_private_mirror_draft_is_untouched(self):
        with self.assertRaisesRegex(ValueError, 'PLUGIN_ROOTS_OVERLAP'):
            prepare(self.catalog, self.source / 'nested', self.source)
        self.mirror.mkdir()
        draft = self.mirror / 'marketplace-submission.json';draft.write_text('private draft')
        self.run_prepare()
        self.assertEqual(draft.read_text(), 'private draft')
        self.assertTrue(all((self.mirror / name).is_file() for name in MIRROR_FILES))


if __name__ == '__main__':
    unittest.main()
