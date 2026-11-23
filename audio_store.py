"""Read and append generated MP3s on the tts-audio branch."""

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path

REF = 'refs/heads/tts-audio'
CLIP_NAME = re.compile(r'[0-9a-f]{64}\.mp3')


def git(*args, env=None, check=True):
    return subprocess.run(['git', *args], stdout=subprocess.PIPE, check=check, env=env)


def fetch_store():
    result = git('ls-remote', '--exit-code', 'origin', REF, check=False)
    if result.returncode == 2:
        return None, set()
    result.check_returncode()
    git('fetch', '--no-tags', 'origin', REF)
    revision = git('rev-parse', 'FETCH_HEAD').stdout.decode('ascii').strip()
    entries = git('ls-tree', '-rz', '--name-only', revision, '--', 'audio').stdout.split(b'\0')
    names = {path[6:].decode('ascii') for path in entries
             if re.fullmatch(rb'audio/[0-9a-f]{64}\.mp3', path)}
    return revision, names


def restore(directory, revision, names):
    directory.mkdir(parents=True, exist_ok=True)
    for name in sorted(names):
        data = git('cat-file', 'blob', f'{revision}:audio/{name}').stdout
        if not data:
            raise ValueError(f'Archived audio is empty: {name}')
        (directory / name).write_bytes(data)


def save(directory, revision, names):
    if not directory.is_dir():
        raise ValueError(f'Missing generated audio directory: {directory}')
    additions = [clip for clip in sorted(directory.iterdir())
                 if clip.name not in names and CLIP_NAME.fullmatch(clip.name) and clip.is_file()]
    if not additions:
        return

    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, 'GIT_INDEX_FILE': str(Path(tmp) / 'index')}
        git('read-tree', revision or '--empty', env=env)
        for clip in additions:
            if not clip.stat().st_size:
                raise ValueError(f'Generated audio is empty: {clip.name}')
            blob = git('hash-object', '-w', '--', str(clip)).stdout.decode('ascii').strip()
            git('update-index', '--add', '--cacheinfo', f'100644,{blob},audio/{clip.name}', env=env)
        tree = git('write-tree', env=env).stdout.decode('ascii').strip()

    parents = ['-p', revision] if revision else []
    commit = git(
        '-c', 'user.name=github-actions[bot]',
        '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
        'commit-tree', tree, *parents, '-m', f'Archive {len(additions)} generated audio clips',
    ).stdout.decode('ascii').strip()
    git('push', 'origin', f'{commit}:{REF}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('restore', 'save'))
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        revision, names = fetch_store()
        operation = restore if args.operation == 'restore' else save
        operation(args.directory.resolve(), revision, names)
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        parser.exit(1, f'Audio archive {args.operation} failed: {error}\n')


if __name__ == '__main__':
    main()
