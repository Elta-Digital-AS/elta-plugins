"""Build Elta MCP plugin packages; never install, authenticate, or publish."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import zipfile

ROOT = Path(__file__).resolve().parent
APP_ID = re.compile(r'(?:plugin_)?asdk_app_[0-9a-f]{32}')
CLIENT_ID = re.compile(r'elta_app_[A-Za-z0-9]{17}')
SECRET = re.compile(r'(?:elta_(?:(?:oat|ort)_(?:local|prod)|(?:oauth_)?(?:local|prod)|cs)_[A-Za-z0-9_.-]{20,}|sb_secret_[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9_.~-]{16,})')


def target_url(value):
    try:
        url = urlsplit(value)
        host = url.hostname or ''
        dns_name = bool(host) and len(host) <= 253 and all(
            re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label)
            for label in host.split('.'))
        # Host interpolation in a client config could leak local environment
        # variables. Accept a literal canonical HTTPS resource only.
        valid = (dns_name and re.fullmatch(r'https://[A-Za-z0-9.-]+(?::443)?/api/mcp', value)
                 and url.username is None and url.password is None and url.port in (None, 443))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('MCP_TARGET_INVALID')
    return value


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def read_source(root, relative):
    file = root / relative
    resolved = file.resolve(strict=True)
    if file.is_symlink() or not resolved.is_relative_to(root.resolve()):
        raise ValueError('PLUGIN_SOURCE_ESCAPE')
    data = file.read_bytes()
    if SECRET.search(data.decode('utf-8')):
        raise ValueError('PLUGIN_SOURCE_SECRET')
    return data


def catalog_digest(catalog):
    canonical = json.dumps(catalog, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(canonical).hexdigest()


def load_catalog(source, policy):
    if policy.get('catalog') != 'mcp-catalog.json':
        raise ValueError('PLUGIN_CATALOG_INVALID')
    catalog = json.loads(read_source(source, policy['catalog']))
    if policy.get('catalogSha256') != catalog_digest(catalog):
        raise ValueError('PLUGIN_CATALOG_DIGEST_MISMATCH')
    if (set(catalog) != {'schemaVersion', 'scopes', 'scopeClasses', 'tools'}
            or type(catalog['schemaVersion']) is not int or catalog['schemaVersion'] != 2):
        raise ValueError('PLUGIN_CATALOG_INVALID')
    scopes, classes, tools = catalog['scopes'], catalog['scopeClasses'], catalog['tools']
    if (not isinstance(scopes, list) or not scopes or any(not isinstance(s, str) or not re.fullmatch(r'[a-z]+(?:-[a-z]+)*:(read|write)', s) for s in scopes)
            or len(scopes) != len(set(scopes)) or not isinstance(classes, dict) or set(classes) != set(scopes)
            or any(classes[s] != s.split(':')[1] for s in scopes) or not isinstance(tools, list) or not tools):
        raise ValueError('PLUGIN_CATALOG_INVALID')
    names, used_scopes = set(), set()
    for tool in tools:
        if (not isinstance(tool, dict) or set(tool) - {'scopeAlternatives'} != {'name', 'operationId', 'method', 'scopes', 'write', 'file', 'destructive'}
                or not isinstance(tool['name'], str) or not re.fullmatch(r'[a-z][a-z0-9_]+', tool['name']) or tool['name'] in names
                or not isinstance(tool['operationId'], str) or not re.fullmatch(r'[a-z][A-Za-z0-9]+', tool['operationId'])
                or any(type(tool[key]) is not bool for key in ['write', 'file', 'destructive'])
                or not isinstance(tool['scopes'], list) or (not tool['scopes'] and not tool.get('scopeAlternatives')) or any(not isinstance(s, str) for s in tool['scopes'])
                or len(tool['scopes']) != len(set(tool['scopes'])) or not set(tool['scopes']) <= set(scopes)
                or tool.get('method') not in {'GET', 'POST', 'PATCH', 'DELETE', 'PUT'}
                or tool['write'] != (tool['method'] != 'GET')
                or tool['destructive'] and not tool['write']):
            raise ValueError('PLUGIN_CATALOG_INVALID')
        alternatives = tool.get('scopeAlternatives', [])
        if (not isinstance(alternatives, list) or any(not isinstance(scope, str) for scope in alternatives)
                or len(alternatives) != len(set(alternatives)) or not set(alternatives) <= set(scopes)
                or tool['write'] and not any(classes[scope] == 'write' for scope in [*tool['scopes'], *alternatives])):
            raise ValueError('PLUGIN_CATALOG_INVALID')
        names.add(tool['name'])
        used_scopes.update([*tool['scopes'], *alternatives])
    if used_scopes != set(scopes):
        raise ValueError('PLUGIN_CATALOG_INVALID')
    return catalog


def load_matrix(source, catalog, policy, url, connections):
    matrix = json.loads(read_source(source, 'client-matrix.json'))
    if not isinstance(matrix, dict):
        raise ValueError('PLUGIN_NATIVE_MATRIX_INVALID')
    names = {tool['name'] for tool in catalog['tools']}
    required = matrix.get('requiredCases')
    clients = matrix.get('clients')
    if (matrix.get('target') != url or matrix.get('catalogSha256') != policy['catalogSha256'] or not isinstance(required, list) or not required
            or any(not isinstance(case, str) for case in required) or len(required) != len(set(required))
            or not isinstance(clients, list) or not clients):
        raise ValueError('PLUGIN_NATIVE_MATRIX_INVALID')
    surfaces = {'ChatGPT web/Work', 'Claude Code', 'Codex CLI'}
    if (any(not isinstance(client, dict) for client in clients)
            or len(clients) != len(surfaces) or {c.get('surface') for c in clients} != surfaces):
        raise ValueError('PLUGIN_NATIVE_MATRIX_INVALID')
    statuses = {'passed', 'failed', 'blocked', 'unverified'}
    for client in clients:
        if not isinstance(client, dict):
            raise ValueError('PLUGIN_NATIVE_MATRIX_INVALID')
        if (client.get('status') not in statuses or not isinstance(client.get('tools'), dict)
                or set(client['tools']) != names or not isinstance(client.get('cases'), dict)
                or set(client['cases']) != set(required)
                or any(status not in statuses for status in [*client['cases'].values(), *client['tools'].values()])):
            raise ValueError('PLUGIN_NATIVE_MATRIX_INVALID')
        complete = all(status == 'passed' for status in [*client['cases'].values(), *client['tools'].values()])
        if (client['status'] == 'passed') != complete:
            raise ValueError('PLUGIN_NATIVE_MATRIX_INVALID')
        if client['status'] == 'passed' and (client.get('blocker') or not isinstance(client.get('version'), str) or not client['version'].strip()
                or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', client.get('recordedOn', ''))
                or not isinstance(client.get('evidence'), list) or not client['evidence']
                or any(not isinstance(ref, str) or not ref.strip() for ref in client['evidence'])
                or client.get('testedConnection') != connections[client['surface']]):
            raise ValueError('PLUGIN_NATIVE_MATRIX_INVALID')
    passed = all(client['status'] == 'passed' and all(status == 'passed' for status in [*client['cases'].values(), *client['tools'].values()]) for client in clients)
    if (matrix.get('acceptance') not in statuses or (matrix['acceptance'] == 'passed') != passed):
        raise ValueError('PLUGIN_NATIVE_MATRIX_INVALID')
    return matrix


def build(output, mcp_url, openai_app_id, claude_client_id, source=ROOT):
    url = target_url(mcp_url)
    if not isinstance(openai_app_id, str) or not APP_ID.fullmatch(openai_app_id):
        raise ValueError('OPENAI_APP_ID_INVALID')
    if not CLIENT_ID.fullmatch(claude_client_id):
        raise ValueError('CLAUDE_CLIENT_ID_INVALID')
    policy = json.loads(read_source(source, 'policy.json'))
    if (set(policy) != {'name', 'version', 'description', 'author', 'catalog', 'catalogSha256', 'skills'}
            or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', policy['name'])
            or not re.fullmatch(r'\d+\.\d+\.\d+', policy['version'])
            or not isinstance(policy['description'], str) or not policy['description']
            or not isinstance(policy['author'], dict) or not policy['author'].get('name')
            or not isinstance(policy['skills'], list) or not policy['skills']
            or len(policy['skills']) != len(set(policy['skills']))):
        raise ValueError('PLUGIN_POLICY_INVALID')
    catalog = load_catalog(source, policy)
    openai_connection = {'resource': url, 'appId': openai_app_id.removeprefix('plugin_')}
    load_matrix(source, catalog, policy, url, {
        'ChatGPT web/Work': openai_connection, 'Codex CLI': openai_connection,
        'Claude Code': {'resource': url, 'clientId': claude_client_id},
    })
    shared = {}
    for relative in ['skills/_shared/read-contract.md', 'skills/_shared/mcp-contract.md']:
        shared[relative] = read_source(source, relative)
    for skill in policy['skills']:
        if not isinstance(skill, str) or not re.fullmatch(r'[a-z]+(?:-[a-z]+)*', skill):
            raise ValueError('PLUGIN_SKILL_INVALID')
        relative = f'skills/{skill}/SKILL.md'
        shared[relative] = read_source(source, relative)
    required_skills = {'use-elta-tools', 'find-property', 'summarize-observations', 'remediation-overview', 'customer-summary'}
    if set(policy['skills']) != required_skills:
        raise ValueError('PLUGIN_SKILLS_REQUIRED')
    identity = {key: policy[key] for key in ['name', 'version', 'description', 'author']}
    interface = {'displayName': 'Elta', 'shortDescription': 'Read records, view files and make authorized changes.',
                 'developerName': 'Elta Digital AS', 'capabilities': ['Read', 'Write']}
    extension = {'interface': interface}
    extension['apps'] = './.app.json'
    openai = {'.app.json': json_bytes({'apps': {'elta': {'id': openai_app_id.removeprefix('plugin_'), 'required': True}}})}
    openai['plugin.json'] = json_bytes({
        '$schema': 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json',
        **identity, 'extensions': {'com.openai': extension},
    })
    claude = {
        '.claude-plugin/plugin.json': json_bytes({**identity, 'mcpServers': './.mcp.json'}),
        '.mcp.json': json_bytes({'mcpServers': {'elta': {'type': 'http', 'url': url,
            'oauth': {'clientId': claude_client_id, 'scopes': ' '.join(catalog['scopes'])},
        }}}),
    }
    connection = json_bytes({
        'resource': url, 'scopes': catalog['scopes'], 'tools': [tool['name'] for tool in catalog['tools']],
        'catalog': './mcp-catalog.json', 'catalogSha256': policy['catalogSha256'],
        'authority': 'Requested scopes are not grants. Elta enforces the selected workspace, live permissions and consent.',
        'writes': 'Explicit user intent and write consent, owner and environment gates, host approval, idempotency and version rules apply.',
        'files': 'Independent file consent and current record authorization apply; links expire after 60 seconds.',
        'openaiRegistration': 'The publisher must configure the registered MCP app to request these scopes and validate native discovery. The app mapping alone grants no additional access.',
        'nativeEvidence': './client-matrix.json',
    })
    common = {**shared, 'connection.json': connection,
              'mcp-catalog.json': read_source(source, 'mcp-catalog.json'),
              'client-matrix.json': read_source(source, 'client-matrix.json'),
              'README.md': read_source(source, 'INSTALL.md'), 'LICENSE': read_source(source, 'LICENSE')}
    # Validate every byte before creating outputs, including data derived from policy.
    for files in [common, openai, claude]:
        if any(SECRET.search(data.decode('utf-8')) for data in files.values()):
            raise ValueError('PLUGIN_ARTIFACT_SECRET')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    artifacts = []
    for platform, specific in [('openai', openai), ('claude', claude)]:
        files = {**common, **specific}
        folder = output / platform
        for relative, data in sorted(files.items()):
            file = folder / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(data)
        archive = output / f"{policy['name']}-{platform}-{policy['version']}.zip"
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zip:
            for relative, data in sorted(files.items()):
                info = zipfile.ZipInfo(relative, date_time=(2000, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                zip.writestr(info, data, compresslevel=9)
        artifacts.append({'platform': platform, 'path': str(archive), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
    (output / 'artifacts.json').write_bytes(json_bytes({'version': policy['version'], 'artifacts': artifacts}))
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--mcp-url', required=True)
    parser.add_argument('--openai-app-id', required=True, help='Registered MCP app mapping; publisher host scope request must match the catalog')
    parser.add_argument('--claude-client-id', required=True, help='Publisher public OAuth client ID; no secret')
    args = parser.parse_args()
    try:
        print(json.dumps({'artifacts': build(args.output, args.mcp_url, args.openai_app_id, args.claude_client_id)}))
    except (ValueError, FileExistsError, KeyError, TypeError):
        parser.exit(1, 'PLUGIN_BUILD_REFUSED: check catalog/policy, target, public connection IDs, source files and unused output path.\n')


if __name__ == '__main__':
    main()
