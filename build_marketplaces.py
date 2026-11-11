"""Build native Claude/Codex marketplaces. No network, login or publication."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
import zipfile

from build import ROOT, SECRET, json_bytes, load_catalog, read_source, target_url


def build_marketplaces(output, source=ROOT):
    release = json.loads(read_source(source, 'marketplace-release.json'))
    policy = json.loads(read_source(source, 'policy.json'))
    catalog = load_catalog(source, policy)
    url = target_url(release['resource'])
    scopes = release['scopes']
    full = release['profile'] == 'full-catalog'
    if (policy['name'] != 'elta' or not isinstance(release['version'], str)
            or not re.fullmatch(r'\d+\.\d+\.\d+', release['version'])
            or release['profile'] not in {'read-compatible', 'full-catalog'} or release['oauthRegistration'] != 'dynamic'
            or not isinstance(scopes, list) or not scopes or any(not isinstance(scope, str) for scope in scopes)
            or len(scopes) != len(set(scopes))
            or any(scope not in catalog['scopeClasses'] for scope in scopes)
            or (full and set(scopes) != set(catalog['scopes']))
            or (not full and any(catalog['scopeClasses'][scope] != 'read' for scope in scopes))):
        raise ValueError('NATIVE_RELEASE_SCOPES_INVALID')
    identity = {'name': policy['name'], 'version': release['version'],
                'description': 'Use Elta tools within your personal workspace permissions and consent.',
                'author': policy['author']}
    logo = source / 'assets/elta-logo.png'
    if logo.is_symlink() or not logo.resolve(strict=True).is_relative_to(source.resolve()):
        raise ValueError('PLUGIN_SOURCE_ESCAPE')
    logo_bytes = logo.read_bytes()
    if not logo_bytes.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('PLUGIN_LOGO_INVALID')
    if SECRET.search(logo_bytes.decode('latin1')):
        raise ValueError('PLUGIN_SOURCE_SECRET')
    shared = {str(file.relative_to(source)): read_source(source, str(file.relative_to(source)))
              for file in (source / 'skills').rglob('*.md')}
    contract = 'skills/_shared/mcp-contract.md'
    shared[contract] = (("Installed profile: full-catalog. File and write access require explicit consent and live gates. "
                        if full else "Installed profile: read-compatible staging. This release requests only read scopes. ") +
                        "Use the connected server's discovered tools and your grant. File delivery and writes "
                        "still require native workflow verification; do not infer authority from installation.\n\n").encode() + shared[contract]
    shared.update({'README.md': read_source(source, 'MARKETPLACE-INSTALL.md'),
                   'LICENSE': read_source(source, 'LICENSE'),
                   'mcp-catalog.json': read_source(source, 'mcp-catalog.json'),
                   'connection.json': json_bytes(release),
                   'client-matrix.json': read_source(source, 'client-matrix.json')})
    packages = {
        'claude': {'.claude-plugin/plugin.json': json_bytes({**identity, 'mcpServers': './.mcp.json',
                   'icon': './assets/elta-logo.png'}),
                   '.mcp.json': json_bytes({'mcpServers': {'elta': {'type': 'http', 'url': url,
                       'oauth': {'scopes': ' '.join(scopes)}}}})},
        'codex': {'.codex-plugin/plugin.json': json_bytes({**identity,
            'mcpServers': './.mcp.json',
            'interface': {'displayName': 'Elta', 'shortDescription': identity['description'],
                'developerName': 'Elta Digital AS',
                'brandColor': '#079669', 'logo': './assets/elta-logo.png',
                'composerIcon': './assets/elta-logo.png',
                'capabilities': ['Read', 'Write'] if full else ['Read']}}),
            '.mcp.json': json_bytes({'mcpServers': {'elta': {'url': url, 'scopes': scopes}}})},
    }
    files = {}
    for platform, package in packages.items():
        files.update({f'plugins/{platform}/{name}': data for name, data in {**shared, **package}.items()})
    files['.claude-plugin/marketplace.json'] = json_bytes({'name': 'elta',
        'description': 'Elta workspace workflows with personal OAuth sign-in.', 'owner': policy['author'],
        'plugins': [{'name': 'elta', 'source': './plugins/claude', 'version': release['version'],
                     'description': identity['description']}]})
    files['.agents/plugins/marketplace.json'] = json_bytes({'name': 'elta',
        'interface': {'displayName': 'Elta'}, 'plugins': [{'name': 'elta',
        'source': {'source': 'local', 'path': './plugins/codex'},
        'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_USE'}, 'category': 'Productivity'}]})
    if any(SECRET.search(data.decode('utf8')) for data in files.values()):
        raise ValueError('PLUGIN_ARTIFACT_SECRET')
    for platform in packages:
        files[f'plugins/{platform}/assets/elta-logo.png'] = logo_bytes
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, data in sorted(files.items()):
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    archives = []
    for platform in packages:
        archive = output / f"elta-{platform}-{release['version']}.zip"
        prefix = f'plugins/{platform}/'
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as bundle:
            for name, data in sorted(files.items()):
                if not name.startswith(prefix):
                    continue
                entry = zipfile.ZipInfo(name.removeprefix(prefix), date_time=(2000, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(entry, data)
        archives.append({'file': archive.name, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
    (output / 'artifacts.json').write_bytes(json_bytes({'version': release['version'], 'archives': archives}))
    return archives


def check_committed(source=ROOT):
    with tempfile.TemporaryDirectory() as scratch:
        output = Path(scratch) / 'generated'
        build_marketplaces(output, source)
        for name in ['plugins', '.claude-plugin', '.agents']:
            expected = {str(p.relative_to(output)): p.read_bytes() for p in (output / name).rglob('*') if p.is_file()}
            actual = {str(p.relative_to(source)): p.read_bytes() for p in (source / name).rglob('*') if p.is_file()}
            if expected != actual:
                raise ValueError('NATIVE_MARKETPLACE_DRIFT: ' + name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check_committed()
        print('NATIVE_MARKETPLACES_MATCH')
    elif args.output:
        print(json.dumps(build_marketplaces(args.output)))
    else:
        parser.error('use --output or --check')
