import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

from build import APP_ID, ROOT, build, target_url

URL = 'https://sta.elta.no/api/mcp'
APP = 'asdk_app_' + 'a' * 32
CLIENT = 'elta_app_AbCdEfGhIjKlMnOpQ'


class BuildTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)

    def run_build(self, name='output', **options):
        return build(self.root / name, options.pop('mcp_url', URL),
                     options.pop('openai_app_id', APP), options.pop('claude_client_id', CLIENT), **options)

    def source(self):
        path = self.root / 'source'
        shutil.copytree(ROOT, path, ignore=shutil.ignore_patterns('__pycache__', '.git', 'dist'))
        return path

    def test_archives_are_deterministic_and_contain_only_complete_packages(self):
        first = self.run_build('first')
        second = self.run_build('second')
        self.assertEqual([a['sha256'] for a in first], [a['sha256'] for a in second])
        for artifact in first:
            archive = Path(artifact['path'])
            self.assertEqual(artifact['sha256'], hashlib.sha256(archive.read_bytes()).hexdigest())
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(len(z.namelist()), 11)
                self.assertEqual(len([p for p in z.namelist() if p.endswith('/SKILL.md')]), 4)
                self.assertFalse(any(p.startswith('/') or '..' in Path(p).parts for p in z.namelist()))
                self.assertIn('skills/_shared/read-contract.md', z.namelist())
                self.assertIn('client-matrix.json', z.namelist())
                self.assertEqual(z.read('LICENSE'), (ROOT / 'LICENSE').read_bytes())
                connection = json.loads(z.read('connection.json'))
                self.assertEqual(connection['resource'], URL)
                self.assertEqual(connection['scopes'], ['properties:read', 'observations:read'])
                matrix = json.loads(z.read('client-matrix.json'))
                self.assertEqual(matrix, json.loads((ROOT / 'client-matrix.json').read_text()))
                native_pass = all(c['status'] == 'passed' and all(c['cases'].get(case) == 'passed' for case in matrix['requiredCases']) for c in matrix['clients'])
                self.assertEqual(matrix['acceptance'] == 'passed', native_pass)

    def test_platforms_share_exact_skill_bytes_and_keep_their_own_connection_shapes(self):
        self.run_build()
        output = self.root / 'output'
        for file in (output / 'openai/skills').rglob('*.md'):
            relative = file.relative_to(output / 'openai')
            self.assertEqual(file.read_bytes(), (output / 'claude' / relative).read_bytes())
        manifest = json.loads((output / 'openai/plugin.json').read_text())
        self.assertEqual(manifest['version'], json.loads((ROOT / 'package.json').read_text())['version'])
        self.assertEqual(manifest['extensions']['com.openai']['apps'], './.app.json')
        self.assertEqual(manifest['extensions']['com.openai']['interface']['capabilities'], ['Read'])
        app = json.loads((output / 'openai/.app.json').read_text())
        self.assertEqual(app['apps']['elta'], {'id': APP, 'required': True})
        claude = json.loads((output / 'claude/.mcp.json').read_text())
        self.assertEqual(claude, {'mcpServers': {'elta': {'type': 'http', 'url': URL,
                         'oauth': {'clientId': CLIENT, 'scopes': 'properties:read observations:read'}}}})
        self.assertFalse((output / 'openai/.mcp.json').exists())
        self.assertFalse((output / 'claude/plugin.json').exists())

    def test_ui_plugin_identifier_maps_to_registered_app_identifier(self):
        self.assertTrue(APP_ID.fullmatch('plugin_' + APP))
        self.run_build(openai_app_id='plugin_' + APP)
        app = json.loads((self.root / 'output/openai/.app.json').read_text())
        self.assertEqual(app['apps']['elta']['id'], APP)

    def test_rejects_credentials_queries_fragments_non_https_or_other_resources(self):
        for url in ['http://sta.elta.no/api/mcp', 'https://user:secret@sta.elta.no/api/mcp',
                    URL + '?access_token=secret', URL + '#secret', URL + '/extra',
                    'https://sta.elta.no/api/v1', 'https://sta.elta.no:444/api/mcp',
                    'https://sta.elta.no /api/mcp', 'https://sta.elta.no:bad/api/mcp', 'https://${API_KEY}.example.com/api/mcp',
                    'https://%24SECRET.example.com/api/mcp', URL + '?', URL + '#',
                    'https://@sta.elta.no/api/mcp']:
            with self.subTest(url=url), self.assertRaisesRegex(ValueError, 'MCP_TARGET_INVALID'):
                target_url(url)
        self.assertEqual(target_url(URL), URL)

    def test_rejects_credential_shaped_or_malformed_public_identifiers(self):
        for value in ['', 'elta_prod_' + 'a' * 64, 'sk-' + 'a' * 64, APP + '/secret']:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'OPENAI_APP_ID_INVALID'):
                self.run_build(openai_app_id=value)
        for value in ['', 'Bearer ' + 'a' * 64, 'elta_cs_' + 'a' * 64, CLIENT + '/secret']:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'CLAUDE_CLIENT_ID_INVALID'):
                self.run_build(claude_client_id=value)
        self.assertFalse((self.root / 'output').exists())

    def test_refuses_overwriting_an_existing_output(self):
        folder = self.root / 'output'
        folder.mkdir()
        file = folder / 'keep.txt'
        file.write_text('user work')
        with self.assertRaises(FileExistsError):
            self.run_build()
        self.assertEqual(file.read_text(), 'user work')

    def test_refuses_skill_paths_outside_the_package(self):
        source = self.source()
        target = source / 'skills/find-property/SKILL.md'
        target.unlink()
        secret = self.root / 'private.md'
        secret.write_text('synthetic private file')
        target.symlink_to(secret)
        with self.assertRaisesRegex(ValueError, 'PLUGIN_SOURCE_ESCAPE'):
            self.run_build(source=source)
        self.assertFalse((self.root / 'output').exists())

    def test_refuses_accidental_secrets_even_in_reference_text(self):
        source = self.source()
        (source / 'skills/_shared/read-contract.md').write_text('Bearer ' + 'a' * 32)
        with self.assertRaisesRegex(ValueError, 'PLUGIN_SOURCE_SECRET'):
            self.run_build(source=source)
        self.assertFalse((self.root / 'output').exists())

    def test_rejects_write_scopes_or_additional_tools_in_policy(self):
        source = self.source()
        file = source / 'policy.json'
        original = json.loads(file.read_text())
        for field, value in [('scopes', original['scopes'] + ['observations:write']),
                             ('tools', original['tools'] + ['remove_property_observation']),
                             ('name', '../escape'), ('version', '../../escape')]:
            policy = copy.deepcopy(original)
            policy[field] = value
            file.write_text(json.dumps(policy))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'PLUGIN_POLICY_INVALID'):
                self.run_build(source=source)



if __name__ == '__main__':
    unittest.main()
