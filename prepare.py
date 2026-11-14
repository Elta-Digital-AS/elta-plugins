"""Prepare derived plugin sources locally, or check without changing either tree."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True

from plugin_common import (ROOT, catalog_digest, json_bytes, load_catalog,
                           load_matrix, read_source)
from build_marketplaces import build_marketplaces

MIRROR_FILES = ('build.py', 'plugin_common.py', 'test_build.py', 'policy.json',
                'package.json', 'mcp-catalog.json', 'README.md', 'INSTALL.md',
                'client-matrix.json', 'native-cases.json', 'LICENSE', 'RELEASE-HISTORY.md')
NATIVE_TREES = ('plugins', '.claude-plugin', '.agents')


def safe_path(root, name):
    path = root / name
    # Reject symlinks at every level, including ones that point inside the root.
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError('PLUGIN_SOURCE_ESCAPE')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('PLUGIN_SOURCE_ESCAPE')
    return path


def tree(root, name):
    base = safe_path(root, name)
    files = {}
    for path in sorted(base.rglob('*')):
        relative = str(path.relative_to(root))
        safe_path(root, relative)
        if path.is_file():
            files[relative] = path.read_bytes()
    return files


def reconciled_matrix(raw, old_catalog, catalog, resource):
    matrix = json.loads(raw)
    old_digest = catalog_digest(old_catalog)
    digest = catalog_digest(catalog)
    # Validate the complete old record before preserving or invalidating it.
    # Connections are evidence, not new registration inputs.
    if not isinstance(matrix, dict) or not isinstance(matrix.get('clients'), list):
        raise ValueError('PLUGIN_NATIVE_MATRIX_INVALID')
    connections = {c['surface']: c.get('testedConnection')
                   for c in matrix['clients'] if isinstance(c, dict) and 'surface' in c}
    with tempfile.TemporaryDirectory() as scratch:
        source = Path(scratch)
        (source / 'client-matrix.json').write_bytes(raw)
        # The matrix is written before the catalog. A retry may therefore see
        # an already-prepared matrix beside the previous catalog. Validate it
        # against the matching candidate, not against stale metadata.
        prepared = matrix.get('catalogSha256') == digest
        load_matrix(source, catalog if prepared else old_catalog,
                    {'catalogSha256': digest if prepared else old_digest}, matrix.get('target'), connections)
    if matrix['catalogSha256'] == digest and matrix['target'] == resource:
        return raw, {}
    # A metadata change cannot prove workflow compatibility. Keep the exact old
    # bytes (including failures/blockers/evidence/connection) with their digest.
    history = {f'acceptance-history/{hashlib.sha256(raw).hexdigest()}.json': raw}
    matrix = copy.deepcopy(matrix)
    matrix.update(catalogSha256=digest, target=resource, acceptance='unverified', recordedOn=None)
    for client in matrix['clients']:
        client.update(status='unverified', version=None, recordedOn=None,
                      testedConnection=None, evidence=[],
                      blocker='Catalog or target changed; native acceptance must be repeated.')
        client['tools'] = {t['name']: 'unverified' for t in catalog['tools']}
        client['cases'] = {case: 'unverified' for case in matrix['requiredCases']}
    return json_bytes(matrix), history


def prepare(catalog_path, mirror, source=ROOT, check=False):
    source, mirror, catalog_path = Path(source).absolute(), Path(mirror).absolute(), Path(catalog_path).absolute()
    safe_path(source, '.')
    safe_path(mirror, '.')
    if source.resolve().is_relative_to(mirror.resolve()) or mirror.resolve().is_relative_to(source.resolve()):
        raise ValueError('PLUGIN_ROOTS_OVERLAP')
    policy = json.loads(read_source(source, 'policy.json'))
    old_catalog_bytes = read_source(source, 'mcp-catalog.json')
    old_catalog = json.loads(old_catalog_bytes)
    catalog = json.loads(read_source(catalog_path.parent, catalog_path.name))
    release_bytes = read_source(source, 'marketplace-release.json')
    release = json.loads(release_bytes)
    policy['catalogSha256'] = catalog_digest(catalog)
    if release['profile'] == 'full-catalog':
        release['scopes'] = catalog['scopes']
    matrix, history = reconciled_matrix(read_source(source, 'client-matrix.json'),
                                        old_catalog, catalog, release['resource'])
    if history:
        history[f'acceptance-history/{hashlib.sha256(release_bytes).hexdigest()}.release.json'] = release_bytes
    if history or json.loads(matrix)['acceptance'] == 'unverified':
        # Also finish this invalidation when a prior run stopped after the matrix.
        release['fullCatalogAcceptance'] = 'unverified; current matrix requires native acceptance'
    # Authored public files are the source of truth. Copy only the explicit
    # distributable surface, never private drafts, credentials or .git files.
    shared_names = [*MIRROR_FILES, *tree(source, 'skills')]
    shared = {name: read_source(source, name) for name in shared_names}
    shared.update({'mcp-catalog.json': old_catalog_bytes if catalog == old_catalog else json_bytes(catalog), 'policy.json': json_bytes(policy),
                   'client-matrix.json': matrix})
    derived = {name: shared[name] for name in ('mcp-catalog.json', 'policy.json', 'client-matrix.json')}
    derived['marketplace-release.json'] = json_bytes(release)
    derived.update(history)
    with tempfile.TemporaryDirectory() as scratch:
        candidate = Path(scratch).resolve() / 'source'
        candidate.mkdir()
        for name, data in {**shared, **derived,
                           'MARKETPLACE-INSTALL.md': read_source(source, 'MARKETPLACE-INSTALL.md')}.items():
            path = candidate / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        logo = safe_path(source, 'assets/elta-logo.png').read_bytes()
        (candidate / 'assets').mkdir()
        (candidate / 'assets/elta-logo.png').write_bytes(logo)
        load_catalog(candidate, policy)
        load_matrix(candidate, catalog, policy, release['resource'],
                    {c['surface']: c.get('testedConnection') for c in json.loads(matrix)['clients']})
        generated = Path(scratch).resolve() / 'generated'
        build_marketplaces(generated, candidate)
        for name in NATIVE_TREES:
            derived.update(tree(generated, name))
    # Resolve and inspect the entire write set before the first mutation. Check
    # does the same calculations, but does not write or create cache directories.
    changes = []
    for root, expected in ((source, derived), (mirror, shared)):
        existing = {}
        for name in (NATIVE_TREES if root == source else ('skills',)):
            existing.update(tree(root, name))
        for name in sorted(set(existing) | set(expected)):
            path = safe_path(root, name)
            current = path.read_bytes() if path.exists() else None
            desired = expected.get(name)
            if current != desired:
                changes.append((path, desired))
        for name, data in history.items() if root == source else ():
            path = safe_path(root, name)
            if path.exists() and path.read_bytes() != data:
                raise ValueError('PLUGIN_EVIDENCE_HISTORY_CONFLICT')
    if check and changes:
        raise ValueError('PLUGIN_PREPARE_DRIFT: ' + ', '.join(str(path) for path, _ in changes))
    if not check:
        for path, data in changes:
            if data is None:
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
    return len(changes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', required=True, type=Path)
    parser.add_argument('--mirror', required=True, type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        count = prepare(args.catalog, args.mirror, check=args.check)
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f'PLUGIN_PREPARE_REFUSED: {error}\n')
    print(f'PLUGIN_PREPARED changes={count} check={str(args.check).lower()}')


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    main()
