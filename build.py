"""Build private Elta plugin packages; never install, authenticate, or publish."""
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
READ_TOOLS = {'list_properties', 'get_property', 'list_property_placements', 'list_property_observations', 'get_property_observation'}
SECRET = re.compile(r'(?:elta_(?:(?:oauth_)?(?:local|prod)|cs)_[A-Za-z0-9_.-]{20,}|sb_secret_[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9_.~-]{16,})')


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


def build(output, mcp_url, openai_app_id, claude_client_id, source=ROOT):
    url = target_url(mcp_url)
    if not APP_ID.fullmatch(openai_app_id):
        raise ValueError('OPENAI_APP_ID_INVALID')
    if not CLIENT_ID.fullmatch(claude_client_id):
        raise ValueError('CLAUDE_CLIENT_ID_INVALID')
    policy = json.loads(read_source(source, 'policy.json'))
    if (not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', policy['name'])
            or not re.fullmatch(r'\d+\.\d+\.\d+', policy['version'])
            or set(policy['scopes']) != {'properties:read', 'observations:read'}
            or len(policy['scopes']) != 2 or set(policy['tools']) != READ_TOOLS
            or len(policy['tools']) != 5):
        raise ValueError('PLUGIN_POLICY_INVALID')
    shared = {'skills/_shared/read-contract.md': read_source(source, 'skills/_shared/read-contract.md')}
    for skill in policy['skills']:
        if not re.fullmatch(r'[a-z]+(?:-[a-z]+)*', skill):
            raise ValueError('PLUGIN_SKILL_INVALID')
        relative = f'skills/{skill}/SKILL.md'
        shared[relative] = read_source(source, relative)
    if len(shared) != 5:
        raise ValueError('PLUGIN_SKILLS_REQUIRED')
    identity = {key: policy[key] for key in ['name', 'version', 'description', 'author']}
    # UI plugin URLs use a plugin_ prefix; app references use the underlying app id.
    app_id = openai_app_id.removeprefix('plugin_')
    openai = {
        'plugin.json': json_bytes({
            '$schema': 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json',
            **identity,
            'extensions': {'com.openai': {
                'apps': './.app.json',
                'interface': {'displayName': 'Elta (read-only)', 'shortDescription': 'Read properties and recorded findings.',
                              'developerName': 'Elta Digital AS', 'capabilities': ['Read']},
            }},
        }),
        '.app.json': json_bytes({'apps': {'elta': {'id': app_id, 'required': True}}}),
    }
    claude = {
        '.claude-plugin/plugin.json': json_bytes({**identity, 'mcpServers': './.mcp.json'}),
        '.mcp.json': json_bytes({'mcpServers': {'elta': {
            'type': 'http', 'url': url,
            'oauth': {'clientId': claude_client_id, 'scopes': ' '.join(policy['scopes'])},
        }}}),
    }
    connection = json_bytes({'resource': url, 'scopes': policy['scopes'], 'tools': policy['tools'],
                             'openaiRegistration': 'Use the existing registered MCP app with exactly these scopes.',
                             'claudeRegistration': 'Use a public OAuth client; register the host callback exactly.',
                             'nativeEvidence': './client-matrix.json'})
    common = {**shared, 'connection.json': connection,
              'client-matrix.json': read_source(source, 'client-matrix.json'),
              'README.md': read_source(source, 'INSTALL.md'),
              'LICENSE': read_source(source, 'LICENSE')}
    output = Path(output)
    # Refuse an existing output; never erase a user's folder or stale artifacts.
    output.mkdir(parents=True, exist_ok=False)
    artifacts = []
    for platform, specific in [('openai', openai), ('claude', claude)]:
        files = {**common, **specific}
        folder = output / platform
        for relative, data in sorted(files.items()):
            if SECRET.search(data.decode('utf-8')):
                raise ValueError('PLUGIN_ARTIFACT_SECRET')
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
    parser.add_argument('--openai-app-id', required=True, help='Registered MCP app ID or its plugin_ URL identifier; not an OAuth client ID')
    parser.add_argument('--claude-client-id', required=True, help='Registered public OAuth client ID; no secret')
    args = parser.parse_args()
    try:
        print(json.dumps({'artifacts': build(args.output, args.mcp_url, args.openai_app_id, args.claude_client_id)}))
    except (ValueError, FileExistsError):
        parser.exit(1, 'PLUGIN_BUILD_REFUSED: check target, public connection IDs, source files and unused output path.\n')


if __name__ == '__main__':
    main()
