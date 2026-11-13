"""Build Elta MCP plugin packages; never install, authenticate, or publish."""
import argparse
import json
from pathlib import Path
import re
from plugin_common import (ROOT, SECRET, catalog_digest, json_bytes, load_catalog,
                           load_matrix, read_source, target_url, write_archive)

APP_ID = re.compile(r'(?:plugin_)?asdk_app_[0-9a-f]{32}')
CLIENT_ID = re.compile(r'elta_app_[A-Za-z0-9]{17}')
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
    for file in (source / 'skills/_shared').rglob('*.md'):
        relative = str(file.relative_to(source))
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
              'README.md': read_source(source, 'INSTALL.md'),
              'RELEASE-HISTORY.md': read_source(source, 'RELEASE-HISTORY.md'), 'LICENSE': read_source(source, 'LICENSE')}
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
        digest = write_archive(archive, files, compresslevel=9)
        artifacts.append({'platform': platform, 'path': str(archive), 'sha256': digest})
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
