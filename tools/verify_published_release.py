"""Fresh-download and verify a published TileShift release without changing it.

Only the requested private download directory is written. GitHub, Git, the local
build and all ZIP members are read-only; no active-work journal is ever opened.
Run --self-test to exercise corruption/omission fixtures without network access.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import subprocess
import unittest
from unittest import mock
import warnings
import uuid
import zipfile
import zlib


ROOT = Path(__file__).resolve().parents[1]
FORWARD_COUNTS = dict(red=222, blue=222, yellow=223, gold=368, silver=368, crystal=388)
BETA_EXCEPTIONS = {('gold', 'SAFARI_ZONE_BETA'), ('silver', 'SAFARI_ZONE_BETA')}
HEX256 = re.compile(r'[0-9a-f]{64}')


class VerificationError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def output(command, *, cwd=ROOT, data=None):
    result = subprocess.run(command, cwd=cwd, input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise VerificationError(f'{command[0]} failed: {result.stderr.decode("utf-8", "replace").strip()}')
    return result.stdout


def gh_json(endpoint):
    return json.loads(output(['gh', 'api', endpoint]).decode('utf-8'))


def commit_from_ref(repo, ref):
    obj = ref['object']
    seen = set()
    while obj['type'] == 'tag':
        require(obj['sha'] not in seen and len(seen) < 8, 'Invalid/cyclic annotated release tag')
        seen.add(obj['sha'])
        obj = gh_json(f'repos/{repo}/git/tags/{obj["sha"]}')['object']
    require(obj['type'] == 'commit', 'Release ref does not resolve to a commit')
    return obj['sha']


def expected_assets(version):
    archives = [f'TileShift-v{version}.zip',
                f'TileShift-Gen1-Gen2-All-Areas-Comparisons-v{version}.zip',
                f'TileShift-Gen2-in-Gen3-Comparisons-v{version}.zip']
    return {name for archive in archives for name in (archive, archive + '.sha256')}


def snapshot(repo, version, head):
    paths = [f'repos/{repo}/releases/latest', f'repos/{repo}/git/ref/heads/main',
             f'repos/{repo}/git/ref/tags/v{version}']
    with ThreadPoolExecutor(max_workers=3) as pool:
        release, main_ref, tag_ref = list(pool.map(gh_json, paths))
    require(release['tag_name'] == 'v' + version, 'Requested version is not the latest GitHub release')
    require(not release.get('draft') and not release.get('prerelease'), 'Latest release must be published and stable')
    require(commit_from_ref(repo, main_ref) == head, 'Published main differs from local Git HEAD')
    require(commit_from_ref(repo, tag_ref) == head, 'Published release tag differs from local Git HEAD')
    names = [item['name'] for item in release['assets']]
    require(len(names) == len(set(names)) and set(names) == expected_assets(version),
            'Published release does not contain exactly the six expected assets')
    for item in release['assets']:
        require(item.get('state') == 'uploaded', f'Asset is not fully uploaded: {item["name"]}')
        require(re.fullmatch(r'sha256:[0-9a-f]{64}', item.get('digest') or ''),
                f'GitHub API SHA256 is absent/invalid: {item["name"]}')
    return release


def publication_identity(release):
    return (release['id'], release['tag_name'], sorted(
        (a['id'], a['name'], a['size'], a['digest']) for a in release['assets']))


def safe_member(name):
    require(isinstance(name, str) and name and '\\' not in name and ':' not in name
            and not any(ord(c) < 32 for c in name), f'Unsafe archive member: {name!r}')
    path = PurePosixPath(name)
    require(not path.is_absolute() and all(p not in ('', '.', '..') for p in name.split('/')),
            f'Unsafe/noncanonical archive member: {name!r}')
    require(path.as_posix() == name, f'Noncanonical archive member: {name!r}')
    return name


def zip_members(bundle):
    infos = bundle.infolist()
    names = [safe_member(info.filename) for info in infos]
    require(len(names) == len(set(names)), 'ZIP contains duplicate member names')
    require(not any(info.is_dir() for info in infos), 'Unexpected directory entries in release ZIP')
    require(not any((info.external_attr >> 16) & 0o170000 == 0o120000 for info in infos),
            'Release ZIP contains symbolic links')
    require(bundle.testzip() is None, 'ZIP CRC roundtrip failed')
    return set(names)


def verify_asset(item, directory, build):
    name = item['name']; downloaded = directory / name; local = build / name
    require(downloaded.is_file() and local.is_file(), f'Missing downloaded/local build asset: {name}')
    require(downloaded.stat().st_size == local.stat().st_size == item['size'],
            f'Asset byte size differs from API/local build: {name}')
    digest = hashlib.sha256()
    with downloaded.open('rb') as fresh, local.open('rb') as source:
        while True:
            block = fresh.read(4 * 1024 * 1024)
            require(block == source.read(len(block) if block else 1), f'Download differs from local build bytes: {name}')
            if not block:
                break
            digest.update(block)
    value = digest.hexdigest()
    require(item['digest'] == 'sha256:' + value, f'API SHA256 differs from fresh downloaded bytes: {name}')
    return dict(name=name, bytes=item['size'], sha256=value,
                api_sha256_verified=True, fresh_download_matches_local_build_bytes=True)


def verify_checksum(text, archive_name, digest):
    match = re.fullmatch(r'([0-9a-fA-F]{64})[ \t]+\*?([^\r\n]+)\r?\n?', text)
    require(match is not None and match[1].lower() == digest and match[2] == archive_name,
            f'Checksum digest or filename differs: {archive_name}.sha256')


def compare_git_batch(members, payload):
    """Verify one cat-file --batch response in the exact request/member order."""
    position = 0
    for name, content in members:
        end = payload.find(b'\n', position)
        require(end >= 0, f'Truncated Git blob header: {name}')
        header = payload[position:end].split()
        require(len(header) == 3 and header[1] == b'blob', f'Packaged file is absent/not a Git HEAD blob: {name}')
        try:
            size = int(header[2])
        except ValueError as exc:
            raise VerificationError(f'Invalid Git blob size: {name}') from exc
        require(size >= 0, f'Invalid Git blob size: {name}')
        start = end + 1; finish = start + size
        require(payload[start:finish] == content, f'Packaged file differs from Git HEAD: {name}')
        require(payload[finish:finish + 1] == b'\n', f'Truncated Git blob body: {name}')
        position = finish + 1
    require(position == len(payload), 'Unexpected trailing Git cat-file output')


def verify_git_head(root, head, members):
    requests = b''.join(f'{head}:{name}\n'.encode('utf-8') for name, _ in members)
    # One batch invocation for every packaged file; no per-file Git process.
    payload = output(['git', 'cat-file', '--batch'], cwd=root, data=requests)
    compare_git_batch(members, payload)


def verify_manifest(manifest, version):
    require(manifest.get('id') == 'tileshift' and manifest.get('version') == version,
            'Installable manifest id/version differs from release')
    require(re.fullmatch(r'\s*>=\s*0\.3\.96\s*', manifest.get('game_version', '')) is not None,
            'Manifest must contain only the minimum launcher constraint >=0.3.96')


def verify_package(path, version, root, head):
    with zipfile.ZipFile(path) as bundle:
        names = zip_members(bundle)
        require(names and all(name.startswith('tileshift/') for name in names), 'Installable ZIP must contain only tileshift/ files')
        required = {'tileshift/' + name for name in ('manifest.json', 'main.lua', 'README.md', 'CREDITS.md', 'LICENSE')}
        require(required <= names, 'Installable ZIP lacks required mod files')
        members = [(name.removeprefix('tileshift/'), bundle.read(name)) for name in sorted(names)]
        verify_git_head(root, head, members)
        manifest = json.loads(bundle.read('tileshift/manifest.json'))
        verify_manifest(manifest, version)
        return dict(files=len(names), all_members_match_git_head=True, one_git_cat_file_batch=True,
                    zip_roundtrip_verified=True, manifest_version=manifest['version'],
                    launcher_constraint=manifest['game_version'], maximum_launcher_version=False)


def scene_key(record):
    require(isinstance(record, dict) and isinstance(record.get('game'), str)
            and isinstance(record.get('map'), str) and record['map'], 'Invalid comparison/inventory scene identity')
    return record['game'], record['map']


def digest_field(value, label):
    require(isinstance(value, str) and HEX256.fullmatch(value), f'Invalid SHA256 metadata: {label}')
    return value


def forward_inventory(metadata, inventory, comparisons, authority=None):
    records = inventory.get('scenes')
    require(isinstance(records, list), 'Full forward gallery inventory lacks scenes')
    keys = [scene_key(r) for r in records]
    require(len(keys) == len(set(keys)) == 1791, 'Full forward inventory must contain 1791 unique game/map scenes')
    actual_counts = dict(Counter(game for game, _ in keys))
    require(actual_counts == FORWARD_COUNTS, 'Full forward inventory source game counts differ')
    if 'counts' in inventory:
        require(inventory['counts'] == FORWARD_COUNTS, 'Full forward inventory declared counts differ')
    if 'games' in inventory:
        require(inventory['games'] == FORWARD_COUNTS, 'Full forward inventory declared game counts differ')
    if 'total' in inventory:
        require(inventory['total'] == 1791, 'Full forward inventory declared total differs')
    if 'source_inventory_total' in inventory:
        require(inventory['source_inventory_total'] == 1791, 'Full forward source inventory total differs')
    if 'complete_inventory' in inventory:
        require(inventory['complete_inventory'] is True, 'Forward gallery is only a pilot/subset inventory')
    if authority is not None:
        authoritative, authoritative_sha = authority
        expected_keys = [scene_key(r) for r in authoritative['scenes']]
        require(len(expected_keys) == len(set(expected_keys)) == 1791 and set(expected_keys) == set(keys),
                'Forward archive inventory differs from the independent authoritative source inventory')
        require(inventory.get('source_inventory_sha256') == authoritative_sha,
                'Forward archive source inventory fingerprint differs from the authoritative source')
    rendered = [scene_key(r) for r in comparisons]
    require(len(rendered) == len(set(rendered)), 'Full forward comparisons repeat a game/map scene')
    missing = set(keys) - set(rendered)
    require(not (set(rendered) - set(keys)), 'Forward gallery comparison is not in the expected source inventory')
    excluded = {scene_key(r): r for r in records if r.get('status') == 'unrenderable'}
    if missing:
        require(missing == BETA_EXCEPTIONS and set(excluded) == missing and len(rendered) == 1789,
                'Only both actual unrenderable Gold/Silver SAFARI_ZONE_BETA scenes may be omitted')
        for key, record in excluded.items():
            require(isinstance(record.get('reason'), str) and record['reason'].strip(), f'Unrenderable native scene lacks reason: {key}')
            if 'native_art_retained' in record:
                require(record['native_art_retained'] is True, f'Unrenderable Beta must retain native art: {key}')
    else:
        require(len(rendered) == 1791 and not excluded, 'All 1791 native scenes must have actual comparison images')
    # Some schema versions also include a counts summary in the verification.
    declared = metadata.get('inventory')
    if isinstance(declared, dict) and isinstance(declared.get('counts'), dict):
        require(declared['counts'] == FORWARD_COUNTS, 'Gallery verification inventory counts differ')
    if isinstance(declared, dict):
        if 'games' in declared:
            require(declared['games'] == FORWARD_COUNTS, 'Gallery verification inventory game counts differ')
        if 'total' in declared:
            require(declared['total'] == 1791, 'Gallery verification inventory total differs')
        if 'complete' in declared:
            require(declared['complete'] is True, 'Gallery verification declares incomplete source inventory')
        if 'captured' in declared:
            require(declared['captured'] == dict(Counter(g for g, _ in rendered)), 'Gallery verification capture counts differ')
        if 'unrenderable' in declared:
            require(declared['unrenderable'] == len(missing), 'Gallery verification exclusion count differs')
    if 'captured' in inventory:
        require(inventory['captured'] == len(rendered), 'Forward inventory captured total differs')
    if 'unrenderable' in inventory:
        require(inventory['unrenderable'] == len(missing), 'Forward inventory unrenderable total differs')
    by_key = {scene_key(r): r for r in records}
    for item in comparisons:
        entry = by_key[scene_key(item)]
        if 'status' in entry:
            require(entry['status'] == 'captured', 'Forward comparison is not a captured inventory scene')
        for field in ('output', 'comparison_png_sha256'):
            if field in entry:
                require(entry[field] == item[field], f'Inventory/comparison {field} differs')
    return dict(inventory_scenes=1791, comparisons=len(rendered), game_counts=actual_counts,
                exact_expected_game_map_inventory=True, independent_source_inventory_verified=authority is not None,
                authoritative_source_inventory_sha256=authority[1] if authority is not None else None,
                documented_unrenderable=[dict(game=g, map=m, reason=excluded[g, m]['reason']) for g, m in sorted(missing)])


def verify_gallery(path, version, *, forward=False, expected_runtime=None, expected_inventory=None):
    with zipfile.ZipFile(path) as bundle:
        names = zip_members(bundle)
        require({'comparison-verification.json', 'README.txt'} <= names, 'Gallery metadata/README missing')
        metadata = json.loads(bundle.read('comparison-verification.json'))
        require(metadata.get('version') == version, 'Gallery version differs from release')
        if 'status' in metadata:
            require(metadata['status'] == 'passed', 'Gallery verification did not pass')
        runtime_inputs = metadata.get('runtime_inputs')
        require(runtime_inputs is None or isinstance(runtime_inputs, dict), 'Invalid gallery runtime input metadata')
        runtime = metadata.get('runtime_inputs_sha256') or (runtime_inputs or {}).get('sha256')
        if expected_runtime is not None:
            require(runtime == expected_runtime, 'Gallery runtime fingerprint differs from verified local package build')
        comparisons = metadata.get('comparisons')
        require(isinstance(comparisons, list) and comparisons, 'Gallery has no comparison records')
        outputs = []; dimensions = []
        for item in comparisons:
            scene_key(item)
            for field in ('panels_exact_gpu_rgb', 'source_definition_unchanged', 'source_collision_events_unchanged', 'cleanup_restored_native'):
                if field in item:
                    require(item[field] is True, f'Comparison has a failed native-panel/source check: {field}')
            name = safe_member(item.get('output'))
            require(name.lower().endswith('.png') and name in names, f'Comparison PNG missing from archive: {name}')
            digest = digest_field(item.get('comparison_png_sha256'), name)
            data = bundle.read(name)
            require(sha256(data) == digest, f'Comparison PNG metadata hash differs: {name}')
            require(len(data) >= 33 and data[:8] == b'\x89PNG\r\n\x1a\n' and data[12:16] == b'IHDR', f'Comparison is not a PNG: {name}')
            width, height = struct.unpack('>II', data[16:24])
            require(width > 0 and height > 0, f'PNG has invalid dimensions: {name}')
            outputs.append(name); dimensions.append([width, height])
        require(len(outputs) == len(set(outputs)), 'Gallery metadata repeats an output filename')
        require({n for n in names if n.lower().endswith('.png')} == set(outputs), 'Gallery contains PNGs without comparison hash metadata')
        result = dict(comparisons=len(outputs), every_comparison_png_hash_verified=True,
                      zip_roundtrip_verified=True, runtime_inputs_sha256=runtime,
                      output_names_sha256=sha256(('\n'.join(sorted(outputs)) + '\n').encode('utf-8')),
                      comparison_metadata_sha256=sha256(bundle.read('comparison-verification.json')))
        if forward:
            require({'all-area-inventory.json', 'index.html'} <= names, 'Full forward gallery source inventory/index missing')
            inventory_bytes = bundle.read('all-area-inventory.json')
            inventory = json.loads(inventory_bytes)
            result['archive_inventory_sha256'] = sha256(inventory_bytes)
            summary = metadata.get('inventory')
            if isinstance(summary, dict) and 'sha256' in summary:
                require(summary.get('path') == 'all-area-inventory.json' and summary['sha256'] == sha256(inventory_bytes),
                        'Forward gallery inventory metadata fingerprint differs')
            result.update(forward_inventory(metadata, inventory, comparisons, expected_inventory))
            if result['documented_unrenderable']:
                readme = bundle.read('README.txt').decode('utf-8').lower()
                index = bundle.read('index.html').decode('utf-8').lower()
                require(all(word in readme for word in ('1791', '1789', 'safari', 'beta', 'gold', 'silver'))
                        and all(word in index for word in ('1791', '1789', 'safari', 'beta')),
                        'Forward gallery README/index must disclose both unrenderable Beta exclusions/counts')
        return result


def verify_release(version, directory, repo):
    require(re.fullmatch(r'[0-9]+(?:\.[0-9]+)+', version), 'Invalid dotted release version')
    require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo), 'Invalid owner/repository')
    head = output(['git', 'rev-parse', '--verify', 'HEAD^{commit}']).decode().strip()
    release = snapshot(repo, version, head)
    expected = expected_assets(version); build = ROOT / 'build'
    require(all((build / name).is_file() for name in expected), 'One or more expected local build assets are missing')
    directory.mkdir(parents=True, exist_ok=True)
    require(not any((directory / name).exists() for name in expected | {'verification.json'}),
            'Use a fresh private download directory; existing assets/proof will not be overwritten')
    command = ['gh', 'release', 'download', 'v' + version, '--repo', repo, '--dir', str(directory)]
    for name in sorted(expected):
        command += ['--pattern', name]
    output(command)
    assets = [verify_asset(item, directory, build) for item in sorted(release['assets'], key=lambda a: a['name'])]
    by_name = {item['name']: item for item in assets}
    for name in sorted(expected):
        if name.endswith('.zip'):
            verify_checksum((directory / (name + '.sha256')).read_text(encoding='utf-8'), name, by_name[name]['sha256'])
    package_name = f'TileShift-v{version}.zip'
    package = verify_package(directory / package_name, version, ROOT, head)
    build_report = ROOT / 'build/package-verification.json'
    require(build_report.is_file(), 'Local validated package build report is missing')
    local = json.loads(build_report.read_text(encoding='utf-8'))
    require(local.get('version') == version and local.get('sha256') == by_name[package_name]['sha256'],
            'Local package verification report is stale')
    runtime = digest_field(local.get('validated_runtime_sha256'), 'local package runtime')
    with zipfile.ZipFile(directory / package_name) as bundle:
        require(set(local.get('files', {})) == set(bundle.namelist()), 'Local build report/package member inventory differs')
        for name, digest in local['files'].items():
            require(sha256(bundle.read(name)) == digest, f'Local build report member fingerprint differs: {name}')
    galleries = {}
    authority = ROOT.parent / '.work/tileshift-reverse-forward-gallery-inventory/inventory.json'
    expected_inventory = (json.loads(authority.read_bytes()), sha256(authority.read_bytes())) if authority.is_file() else None
    for forward, name in [(True, f'TileShift-Gen1-Gen2-All-Areas-Comparisons-v{version}.zip'),
                          (False, f'TileShift-Gen2-in-Gen3-Comparisons-v{version}.zip')]:
        galleries[name] = verify_gallery(directory / name, version, forward=forward,
                                         expected_runtime=runtime, expected_inventory=expected_inventory if forward else None)
    require(output(['git', 'rev-parse', '--verify', 'HEAD^{commit}']).decode().strip() == head, 'Local HEAD changed during verification')
    final = snapshot(repo, version, head)
    require(publication_identity(final) == publication_identity(release), 'Published release/assets changed during verification')
    proof = dict(status='passed', version=version, repository=repo, latest_release=release['html_url'],
                 commit=head, release_id=release['id'], verified_at_utc=datetime.now(timezone.utc).isoformat(),
                 downloaded_fresh=True, local_build_bytes_identical=True, api_sha256_all_assets_verified=True,
                 asset_count=len(assets), verified_assets=assets, installable_package=package,
                 galleries=galleries, active_work_journal_touched=False,
                 publication_stable_during_verification=True)
    (directory / 'verification.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    return proof


def self_tests():
    fixture_root = (ROOT.parent / '.work/tileshift-release-verifier-fixtures').resolve()
    fixture_root.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def fixture_directory():
        # Ordinary inherited Windows directory ACLs also work in the desktop
        # workspace's restricted process; tempfile's mode0700 ACL does not.
        directory = (fixture_root / ('case-' + uuid.uuid4().hex)).resolve()
        require(directory.is_relative_to(fixture_root), 'Fixture cleanup target leaves the private test directory')
        directory.mkdir()
        try:
            yield directory
        finally:
            # The resolved recursive-cleanup target was checked above.
            shutil.rmtree(directory)

    def png():
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b'\0\0\0\0\xff')) + chunk(b'IEND', b'')

    class Fixtures(unittest.TestCase):
        def test_checksum(self):
            digest = 'a' * 64
            verify_checksum(digest + '  sample.zip\n', 'sample.zip', digest)
            with self.assertRaises(VerificationError):
                verify_checksum(digest + '  wrong.zip\n', 'sample.zip', digest)

        def test_manifest_only_minimum(self):
            verify_manifest(dict(id='tileshift', version='0.32.0', game_version='>=0.3.96'), '0.32.0')
            with self.assertRaises(VerificationError):
                verify_manifest(dict(id='tileshift', version='0.32.0', game_version='>=0.3.96 <=0.3.98'), '0.32.0')

        def test_one_git_batch_and_tamper(self):
            members = [('main.lua', b'hello'), ('manifest.json', b'{}')]
            payload = b'a' * 40 + b' blob 5\nhello\n' + b'b' * 40 + b' blob 2\n{}\n'
            completed = subprocess.CompletedProcess([], 0, payload, b'')
            with mock.patch.object(subprocess, 'run', return_value=completed) as command:
                verify_git_head(ROOT, 'c' * 40, members)
                self.assertEqual(command.call_count, 1)
                self.assertIn('--batch', command.call_args.args[0])
            with self.assertRaises(VerificationError):
                compare_git_batch([('main.lua', b'other'), members[1]], payload)
            with self.assertRaises(VerificationError):
                compare_git_batch(members, b'HEAD:main.lua missing\n')

        def test_asset_bytes_api_and_local(self):
            with fixture_directory() as temporary:
                root = Path(temporary); a = root / 'fresh'; b = root / 'build'; a.mkdir(); b.mkdir()
                (a / 'sample.zip').write_bytes(b'bytes'); (b / 'sample.zip').write_bytes(b'bytes')
                item = dict(name='sample.zip', size=5, digest='sha256:' + sha256(b'bytes'))
                verify_asset(item, a, b)
                with self.assertRaises(VerificationError):
                    verify_asset(dict(item, digest='sha256:' + '0' * 64), a, b)
                (b / 'sample.zip').write_bytes(b'other')
                with self.assertRaises(VerificationError):
                    verify_asset(item, a, b)

        def test_duplicate_or_unsafe_zip(self):
            for name in ('../bad.png', 'C:/bad.png', '/bad.png', 'a\\b.png'):
                with self.assertRaises(VerificationError):
                    safe_member(name)
            stream = io.BytesIO()
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                with zipfile.ZipFile(stream, 'w') as bundle:
                    bundle.writestr('a.txt', b'a'); bundle.writestr('a.txt', b'b')
            stream.seek(0)
            with zipfile.ZipFile(stream) as bundle, self.assertRaises(VerificationError):
                zip_members(bundle)

        def test_gallery_hash_and_unlisted_png(self):
            data = png(); record = dict(game='emerald', map='EM_TEST', output='a.png', comparison_png_sha256=sha256(data))
            with fixture_directory() as temporary:
                path = Path(temporary) / 'gallery.zip'
                def write(content, extra=False):
                    with zipfile.ZipFile(path, 'w') as bundle:
                        bundle.writestr('a.png', content); bundle.writestr('README.txt', 'fixture')
                        bundle.writestr('comparison-verification.json', json.dumps(dict(version='0.32.0', comparisons=[record])))
                        if extra:
                            bundle.writestr('unlisted.png', data)
                write(data); self.assertEqual(verify_gallery(path, '0.32.0')['comparisons'], 1)
                write(data + b'tamper')
                with self.assertRaises(VerificationError):
                    verify_gallery(path, '0.32.0')
                write(data, True)
                with self.assertRaises(VerificationError):
                    verify_gallery(path, '0.32.0')

        def test_full_inventory_and_only_documented_beta_omissions(self):
            records = [dict(game=g, map=f'MAP_{i}') for g, n in FORWARD_COUNTS.items() for i in range(n)]
            for game in ('gold', 'silver'):
                next(r for r in records if r['game'] == game)['map'] = 'SAFARI_ZONE_BETA'
            inventory = dict(scenes=records, counts=FORWARD_COUNTS)
            self.assertEqual(forward_inventory({}, inventory, records)['comparisons'], 1791)
            for record in records:
                if scene_key(record) in BETA_EXCEPTIONS:
                    record.update(status='unrenderable', reason='Actual native renderer failed in this fixture')
            rendered = [r for r in records if scene_key(r) not in BETA_EXCEPTIONS]
            self.assertEqual(forward_inventory({}, inventory, rendered)['comparisons'], 1789)
            with self.assertRaises(VerificationError):
                forward_inventory({}, inventory, rendered[1:])
            with self.assertRaises(VerificationError):
                forward_inventory({}, inventory, rendered + [rendered[0]])

        def test_complete_forward_archive_schema_and_authority(self):
            data = png(); digest = sha256(data); records = []; comparisons = []
            for game, count in FORWARD_COUNTS.items():
                for i in range(count):
                    name = f'{game}/MAP_{i}.png'
                    entry = dict(game=game, map=f'MAP_{i}', output=name, comparison_png_sha256=digest)
                    records.append(dict(entry, status='captured')); comparisons.append(entry)
            authority = dict(total=1791, games=FORWARD_COUNTS, scenes=[dict(game=r['game'], map=r['map']) for r in records])
            source_digest = sha256(json.dumps(authority).encode())
            inventory = dict(total=1791, games=FORWARD_COUNTS, scenes=records, source_inventory_total=1791,
                             source_inventory_sha256=source_digest, captured=1791, unrenderable=0, complete_inventory=True)
            inventory_bytes = json.dumps(inventory).encode()
            metadata = dict(version='0.32.0', status='passed', runtime_inputs_sha256='1' * 64,
                            inventory=dict(path='all-area-inventory.json', sha256=sha256(inventory_bytes),
                                           total=1791, games=FORWARD_COUNTS, captured=FORWARD_COUNTS, unrenderable=0, complete=True),
                            comparisons=comparisons)
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as bundle:
                for record in records:
                    bundle.writestr(record['output'], data)
                bundle.writestr('README.txt', '1791 records and1791 fixture images')
                bundle.writestr('index.html', 'fixture index')
                bundle.writestr('comparison-verification.json', json.dumps(metadata))
                bundle.writestr('all-area-inventory.json', inventory_bytes)
            stream.seek(0)
            result = verify_gallery(stream, '0.32.0', forward=True, expected_runtime='1' * 64,
                                    expected_inventory=(authority, source_digest))
            self.assertEqual(result['comparisons'], 1791)
            self.assertTrue(result['independent_source_inventory_verified'])
            changed = dict(authority, scenes=[dict(authority['scenes'][0], map='WRONG')] + authority['scenes'][1:])
            with self.assertRaises(VerificationError):
                forward_inventory(metadata, inventory, comparisons, (changed, source_digest))

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Fixtures)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    require(result.wasSuccessful(), 'Release-verifier fixture tests failed')
    return dict(status='passed', fixture_tests=result.testsRun, network_calls=0,
                published_state_changed=False, active_work_journal_touched=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', help='Dotted version, with or without the v prefix')
    parser.add_argument('--download-dir', type=Path, help='Fresh private directory for downloads and verification.json')
    parser.add_argument('--repo', default='Bentley734/TileShift')
    parser.add_argument('--self-test', action='store_true', help='Run local corruption/omission fixtures; no downloads/API calls')
    args = parser.parse_args()
    try:
        if args.self_test:
            require(not args.version and not args.download_dir, '--self-test does not accept release/download arguments')
            proof = self_tests()
        else:
            require(args.version is not None and args.download_dir is not None, '--version and --download-dir are required')
            proof = verify_release(args.version.removeprefix('v'), args.download_dir.resolve(), args.repo)
    except (VerificationError, KeyError, ValueError, OSError, zipfile.BadZipFile) as exc:
        parser.exit(1, f'Verification failed: {exc}\n')
    print(json.dumps(proof, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
