import json
from pathlib import Path
import shutil
import tempfile
import unittest

from build import ROOT
from build_marketplaces import build_marketplaces, check_committed


class MarketplaceTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)

    def test_packages_use_discovery_without_credentials_or_private_app_mappings(self):
        output = self.root / 'built'
        build_marketplaces(output)
        release = json.loads((ROOT / 'marketplace-release.json').read_text())
        claude = json.loads((output / 'plugins/claude/.mcp.json').read_text())
        server = claude['mcpServers']['elta']
        self.assertEqual(server['oauth'], {'scopes': ' '.join(release['scopes'])})
        codex = json.loads((output / 'plugins/codex/.mcp.json').read_text())
        self.assertEqual(codex['mcpServers']['elta'], {
            'url': release['resource'], 'scopes': release['scopes']})
        manifest = json.loads((output / 'plugins/codex/.codex-plugin/plugin.json').read_text())
        self.assertEqual(manifest['mcpServers'], './.mcp.json')
        self.assertFalse((output / 'plugins/codex/.app.json').exists())
        for platform in ['claude', 'codex']:
            folder = output / 'plugins' / platform
            self.assertEqual(len(list((folder / 'skills').glob('*/SKILL.md'))), 5)
            self.assertIn('Installed profile:', (folder / 'skills/_shared/mcp-contract.md').read_text())
            self.assertEqual(json.loads((folder / 'connection.json').read_text()), release)
        self.assertEqual(json.loads((output / '.claude-plugin/marketplace.json').read_text())['plugins'][0]['source'], './plugins/claude')
        self.assertEqual(json.loads((output / '.agents/plugins/marketplace.json').read_text())['plugins'][0]['source']['path'], './plugins/codex')

    def test_codex_read_profile_does_not_request_write_scopes(self):
        source = self.root / 'source'
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git', '__pycache__', 'dist'))
        file = source / 'marketplace-release.json'
        release = json.loads(file.read_text())
        release.update(profile='read-compatible', scopes=['properties:read', 'observations:read'])
        file.write_text(json.dumps(release))
        output = self.root / 'read-profile'
        build_marketplaces(output, source)
        server = json.loads((output / 'plugins/codex/.mcp.json').read_text())['mcpServers']['elta']
        self.assertEqual(server['scopes'], release['scopes'])

    def test_native_archives_are_deterministic_and_refuse_overwrite(self):
        self.assertEqual(build_marketplaces(self.root / 'a'), build_marketplaces(self.root / 'b'))
        with self.assertRaises(FileExistsError):
            build_marketplaces(self.root / 'a')

    def test_read_profile_rejects_writes_unknown_scopes_and_path_versions(self):
        source = self.root / 'source'
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git', '__pycache__', 'dist'))
        file = source / 'marketplace-release.json'
        original = json.loads(file.read_text())
        for changes in [{'scopes': ['properties:write']}, {'scopes': ['accounts:read']},
                        {'version': '../../escape'}, {'scopes': ['properties:read', 'properties:read']}]:
            file.write_text(json.dumps({**original, 'profile': 'read-compatible', **changes}))
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'NATIVE_RELEASE_SCOPES_INVALID'):
                build_marketplaces(self.root / 'rejected', source)
            self.assertFalse((self.root / 'rejected').exists())

    def test_full_profile_requires_the_exact_reviewed_scope_set(self):
        source = self.root / 'source'
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git', '__pycache__', 'dist'))
        file = source / 'marketplace-release.json'
        release = json.loads(file.read_text())
        release.update(profile='full-catalog', scopes=['properties:read'])
        file.write_text(json.dumps(release))
        with self.assertRaisesRegex(ValueError, 'NATIVE_RELEASE_SCOPES_INVALID'):
            build_marketplaces(self.root / 'rejected', source)

    def test_committed_marketplaces_are_reproducible(self):
        check_committed()


if __name__ == '__main__':
    unittest.main()
