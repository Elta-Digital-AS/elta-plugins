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

    def test_target_specific_uploads_require_a_nonempty_scope_alternative(self):
        from build import load_catalog, catalog_digest
        source=self.source()
        catalog=json.loads((source/'mcp-catalog.json').read_text())
        tool=next(t for t in catalog['tools'] if t['name']=='start_observation_photo_upload')
        self.assertEqual(tool['scopes'],[])
        self.assertIn('properties:write',tool['scopeAlternatives'])
        policy=json.loads((source/'policy.json').read_text())
        self.assertEqual(load_catalog(source,policy),catalog)
        tool['scopeAlternatives']=[]
        (source/'mcp-catalog.json').write_text(json.dumps(catalog))
        policy['catalogSha256']=catalog_digest(catalog)
        with self.assertRaisesRegex(ValueError,'PLUGIN_CATALOG_INVALID'):
            load_catalog(source,policy)

    def test_archives_are_deterministic_and_contain_only_complete_packages(self):
        first = self.run_build('first')
        second = self.run_build('second')
        self.assertEqual([a['sha256'] for a in first], [a['sha256'] for a in second])
        for artifact in first:
            archive = Path(artifact['path'])
            self.assertEqual(artifact['sha256'], hashlib.sha256(archive.read_bytes()).hexdigest())
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(len(z.namelist()), 14)
                self.assertEqual(len([p for p in z.namelist() if p.endswith('/SKILL.md')]), 5)
                self.assertFalse(any(p.startswith('/') or '..' in Path(p).parts for p in z.namelist()))
                self.assertIn('skills/_shared/read-contract.md', z.namelist())
                self.assertIn('client-matrix.json', z.namelist())
                self.assertEqual(z.read('LICENSE'), (ROOT / 'LICENSE').read_bytes())
                connection = json.loads(z.read('connection.json'))
                self.assertEqual(connection['resource'], URL)
                self.assertEqual(connection['scopes'], json.loads((ROOT / 'mcp-catalog.json').read_text())['scopes'])
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
        self.assertEqual(manifest['extensions']['com.openai']['interface']['capabilities'], ['Read', 'Write'])
        app = json.loads((output / 'openai/.app.json').read_text())
        self.assertEqual(app['apps']['elta'], {'id': APP, 'required': True})
        claude = json.loads((output / 'claude/.mcp.json').read_text())
        self.assertEqual(claude, {'mcpServers': {'elta': {'type': 'http', 'url': URL,
                         'oauth': {'clientId': CLIENT, 'scopes': ' '.join(json.loads((ROOT / 'mcp-catalog.json').read_text())['scopes'])}}}})
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
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'OPENAI_APP_ID_INVALID|OPENAI_CONNECTION_REQUIRED'):
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

    def test_rejects_overrides_or_unsafe_identity_in_policy(self):
        source = self.source()
        file = source / 'policy.json'
        original = json.loads(file.read_text())
        for field, value in [('scopes', ['accounts:write']), ('tools', ['admin_override']),
                             ('name', '../escape'), ('version', '../../escape')]:
            policy = copy.deepcopy(original)
            policy[field] = value
            file.write_text(json.dumps(policy))
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'PLUGIN_POLICY_INVALID'):
                self.run_build(source=source)

    def test_full_catalog_is_packaged_for_both_platforms(self):
        self.run_build()
        catalog = json.loads((ROOT / 'mcp-catalog.json').read_text())
        expected = {row['name'] for row in catalog['tools']}
        for platform in ['openai', 'claude']:
            folder = self.root / 'output' / platform
            self.assertEqual(json.loads((folder / 'mcp-catalog.json').read_text()), catalog)
            connection = json.loads((folder / 'connection.json').read_text())
            self.assertEqual(set(connection['tools']), expected)
            self.assertEqual(set(connection['scopes']), set(catalog['scopes']))

    def test_full_scope_request_and_write_capability_are_honest(self):
        self.run_build()
        output = self.root / 'output'
        manifest = json.loads((output / 'openai/plugin.json').read_text())
        self.assertEqual(manifest['extensions']['com.openai']['interface']['capabilities'], ['Read', 'Write'])
        claude = json.loads((output / 'claude/.mcp.json').read_text())
        scopes = claude['mcpServers']['elta']['oauth']['scopes'].split()
        self.assertEqual(set(scopes), set(json.loads((ROOT / 'mcp-catalog.json').read_text())['scopes']))

    def test_general_workflow_is_included_without_removing_read_summaries(self):
        self.run_build()
        for platform in ['openai', 'claude']:
            folder = self.root / 'output' / platform
            self.assertTrue((folder / 'skills/use-elta-tools/SKILL.md').is_file())
            self.assertTrue((folder / 'skills/_shared/mcp-contract.md').is_file())
            for skill in ['find-property', 'summarize-observations', 'remediation-overview', 'customer-summary']:
                self.assertTrue((folder / f'skills/{skill}/SKILL.md').is_file())


    def test_catalog_digest_detects_an_unreviewed_tool_removal(self):
        source = self.source()
        file = source / 'mcp-catalog.json'
        catalog = json.loads(file.read_text())
        catalog['tools'].pop()
        file.write_text(json.dumps(catalog))
        with self.assertRaisesRegex(ValueError, 'PLUGIN_CATALOG_DIGEST_MISMATCH'):
            self.run_build(source=source)
        self.assertFalse((self.root / 'output').exists())

    def test_rejects_catalog_duplicates_and_inconsistent_authority_flags(self):
        from build import catalog_digest
        source = self.source()
        file = source / 'mcp-catalog.json'
        original = json.loads(file.read_text())
        policy_file = source / 'policy.json'
        original_policy = json.loads(policy_file.read_text())
        mutations = [
            lambda c: c['tools'].append(copy.deepcopy(c['tools'][0])),
            lambda c: c['tools'][0].update(write=not c['tools'][0]['write']),
            lambda c: c['tools'][0].update(file='yes'),
            lambda c: c['tools'][0].update(scopes=['accounts:write']),
            lambda c: c['tools'][0].update(name='../escape'),
            lambda c: c['tools'][0].update(extra='unexpected'),
            lambda c: c['scopes'].append(c['scopes'][0]),
            lambda c: c['scopeClasses'].update({c['scopes'][0]: 'admin'}),
            lambda c: c.update(schemaVersion=True),
        ]
        for change in mutations:
            catalog = copy.deepcopy(original)
            change(catalog)
            file.write_text(json.dumps(catalog))
            policy = copy.deepcopy(original_policy)
            policy['catalogSha256'] = catalog_digest(catalog)
            policy_file.write_text(json.dumps(policy))
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'PLUGIN_CATALOG_INVALID'):
                self.run_build(source=source)
            self.assertFalse((self.root / 'output').exists())

    def test_native_matrix_cannot_claim_pass_with_missing_tools_or_clients(self):
        source = self.source()
        file = source / 'client-matrix.json'
        original = json.loads(file.read_text())
        for mode in ['missing-tool', 'missing-client', 'false-pass', 'unversioned-pass']:
            matrix = copy.deepcopy(original)
            if mode == 'missing-tool':
                matrix['clients'][0]['tools'].pop(next(iter(matrix['clients'][0]['tools'])))
            elif mode == 'missing-client':
                matrix['clients'].pop()
            elif mode == 'false-pass':
                matrix['acceptance'] = 'passed'
            else:
                for client in matrix['clients']:
                    client['status'] = 'passed'
                    client['tools'] = dict.fromkeys(client['tools'], 'passed')
                    client['cases'] = dict.fromkeys(client['cases'], 'passed')
                matrix['acceptance'] = 'passed'
            file.write_text(json.dumps(matrix))
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'PLUGIN_NATIVE_MATRIX_INVALID'):
                self.run_build(source=source)
            self.assertFalse((self.root / 'output').exists())

    def test_malformed_matrix_objects_fail_with_a_clean_refusal(self):
        import subprocess
        import sys
        source = self.source()
        file = source / 'client-matrix.json'
        original = json.loads(file.read_text())
        for value in [[], {**original, 'clients': [None, {}, {}]}]:
            file.write_text(json.dumps(value))
            result = subprocess.run([sys.executable, str(source / 'build.py'),
                '--output', str(self.root / 'output'), '--mcp-url', URL,
                '--openai-app-id', APP, '--claude-client-id', CLIENT],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('PLUGIN_BUILD_REFUSED', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertFalse((self.root / 'output').exists())

    def test_detects_oauth_access_and_refresh_tokens_in_source(self):
        source = self.source()
        for prefix in ['elta_oat_local_', 'elta_ort_prod_', 'elta_cs_']:
            (source / 'skills/_shared/read-contract.md').write_text(prefix + 'x' * 48)
            with self.subTest(prefix=prefix), self.assertRaisesRegex(ValueError, 'PLUGIN_SOURCE_SECRET'):
                self.run_build(source=source)
            self.assertFalse((self.root / 'output').exists())


    def test_native_receipt_metadata_is_bound_to_endpoint_and_registration(self):
        source = self.source()
        file = source / 'client-matrix.json'
        matrix = json.loads(file.read_text())
        for client in matrix['clients']:
            client.pop('blocker', None)
            client.update(status='passed', version='synthetic-validator-test', recordedOn='2026-11-10',
                          evidence=['https://example.invalid/synthetic-not-a-native-proof'])
            client['cases'] = dict.fromkeys(client['cases'], 'passed')
            client['tools'] = dict.fromkeys(client['tools'], 'passed')
            client['testedConnection'] = {'resource': URL, **({'clientId': CLIENT} if client['surface'] == 'Claude Code' else {'appId': APP})}
        matrix['acceptance'] = 'passed'
        file.write_text(json.dumps(matrix))
        self.run_build('bound', source=source)
        with self.assertRaisesRegex(ValueError, 'PLUGIN_NATIVE_MATRIX_INVALID'):
            self.run_build(source=source, claude_client_id='elta_app_ZbCdEfGhIjKlMnOpQ')
        with self.assertRaisesRegex(ValueError, 'PLUGIN_NATIVE_MATRIX_INVALID'):
            self.run_build(source=source, mcp_url='https://other.example/api/mcp')


if __name__ == '__main__':
    unittest.main()
