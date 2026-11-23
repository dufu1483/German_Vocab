import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'audio_store.py'


def run(folder, *args):
    result = subprocess.run(args, cwd=folder, capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


class AudioStoreTest(unittest.TestCase):
    def test_archive_survives_fresh_checkout_and_save_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = root / 'remote.git'
            run(root, 'git', 'init', '--bare', str(remote))
            fixture = SCRIPT.parent / 'audio-preview' / 'broetchen-google-translate.mp3'
            first = root / 'first'
            first.mkdir()
            run(first, 'git', 'init')
            run(first, 'git', 'remote', 'add', 'origin', remote.as_uri())
            source = root / 'generated'
            source.mkdir()
            restore = root / 'restored'
            def archive(cwd, operation, path):
                run(cwd, sys.executable, str(SCRIPT), operation, str(path))

            archive(first, 'restore', restore)
            self.assertEqual(list(restore.iterdir()), [])
            name = 'a' * 64 + '.mp3'
            (source / name).write_bytes(fixture.read_bytes())
            archive(first, 'save', source)
            revision = run(remote, 'git', 'rev-parse', 'refs/heads/tts-audio')

            second = root / 'second'
            second.mkdir()
            run(second, 'git', 'init')
            run(second, 'git', 'remote', 'add', 'origin', remote.as_uri())
            archive(second, 'restore', restore)
            self.assertEqual((restore / name).read_bytes(), fixture.read_bytes())
            archive(second, 'save', source)
            self.assertEqual(run(remote, 'git', 'rev-parse', 'refs/heads/tts-audio'), revision)

            extra = 'b' * 64 + '.mp3'
            (source / name).unlink()
            (source / extra).write_bytes(fixture.read_bytes())
            archive(second, 'save', source)
            fresh = root / 'fresh'
            archive(first, 'restore', fresh)
            self.assertEqual({clip.name for clip in fresh.iterdir()}, {name, extra})
