import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class BuildTest(unittest.TestCase):
    def test_cold_cache_reuses_archived_clip_after_gloss_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            courses = root / 'courses'
            courses.mkdir()
            (courses / 'Lesson.tsv').write_text(
                'category\tspoken\tsingular\tplural\tmeaning_zh\nFruit\tMirabelle\tdie Mirabelle\tdie Mirabellen\t黃李\n',
                encoding='utf-8',
            )
            archive = root / 'archive'
            archive.mkdir()
            name = '3775434e9bf00406a0a295f91071e97456488f9a9c141e226721adea18e2a053.mp3'
            clip = Path('audio-preview/broetchen-google-translate.mp3').read_bytes()
            (archive / name).write_bytes(clip)
            output = root / 'site'
            result = subprocess.run(
                [sys.executable, 'build.py', '--courses', str(courses), '--output', str(output),
                 '--cache', str(root / 'empty'), '--audio-store', str(archive)],
                capture_output=True, text=True, encoding='utf-8',
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('黃李', (output / 'index.html').read_text(encoding='utf-8'))
            self.assertEqual((output / 'audio' / name).read_bytes(), clip)
            with (courses / 'Lesson.tsv').open('a', encoding='utf-8') as lesson:
                lesson.write('Fruit\tKiwi\tdie Kiwi\tdie Kiwis\t奇異果\n')
            (root / 'gtts.py').write_text(
                'from pathlib import Path\n'
                'class gTTSError(Exception):\n    pass\n'
                'class gTTS:\n'
                '    def __init__(self, text, **kwargs):\n        print("synthesized:", text)\n'
                f'    def save(self, path):\n        Path(path).write_bytes({clip!r})\n',
                encoding='utf-8',
            )
            result = subprocess.run(
                [sys.executable, 'build.py', '--courses', str(courses), '--output', str(output),
                 '--cache', str(root / 'empty'), '--audio-store', str(archive)],
                env={**os.environ, 'PYTHONPATH': str(root)},
                capture_output=True, text=True, encoding='utf-8',
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'synthesized: Kiwi')
            self.assertEqual(len(list((output / 'audio').glob('*.mp3'))), 2)

    def assert_rejected(self, body, *messages):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            courses = root / 'courses'
            courses.mkdir()
            (courses / 'Test.tsv').write_text(
                'category\tspoken\tsingular\tplural\tmeaning_zh\n' + body, encoding='utf-8'
            )
            output = root / 'site'
            result = subprocess.run(
                [sys.executable, 'build.py', '--courses', str(courses), '--output', str(output)],
                capture_output=True, text=True, encoding='utf-8',
            )
            self.assertNotEqual(result.returncode, 0)
            for message in messages:
                self.assertIn(message, result.stderr)
            self.assertFalse(output.exists())

    def test_unclosed_quote_reports_its_start_line(self):
        self.assert_rejected(
            'Bread\tBrötchen\tdas Brötchen\tdie Brötchen\t"roll\n'
            'Fruit\tBirne\tdie Birne\tdie Birnen\tpear\n',
            'Test.tsv:2: invalid TSV',
        )

    def test_all_answer_alternatives_need_the_expected_article(self):
        for singular, plural, column in [
            ('das Brötchen|Brötchen', 'die Brötchen', 'singular'),
            ('das Brötchen', 'Brötchen', 'plural'),
            ('das Brötchen', 'der Brötchen', 'plural'),
            ('der', 'die Brötchen', 'singular'),
        ]:
            with self.subTest(column=column, singular=singular, plural=plural):
                self.assert_rejected(
                    f'Bread\tBrötchen\t{singular}\t{plural}\troll\n',
                    f'Test.tsv:2: {column} answer',
                )

    def test_duplicate_rows_report_both_physical_lines(self):
        self.assert_rejected(
            'Bread\tBrötchen\tdas Brötchen\tdie Brötchen\t"小\n麵包"\n'
            'Bread\tBro\u0308tchen\tdas  Brötchen\tdie Brötchen\t小 麵包\n',
            'Test.tsv:4: duplicate', 'line 2',
        )

    def test_invalid_course_reports_line_and_does_not_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            courses = root / "courses"
            courses.mkdir()
            (courses / "Test.tsv").write_text(
                "category\tspoken\tsingular\tplural\tmeaning_zh\nObst\tApfel\t\t\tApple\n",
                encoding="utf-8",
            )
            output = root / "site"
            result = subprocess.run(
                [sys.executable, "build.py", "--courses", str(courses), "--output", str(output)],
                capture_output=True, text=True, encoding="utf-8"
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Test.tsv:2", result.stderr)
            self.assertFalse(output.exists())

    def test_build_packages_course_and_reuses_seeded_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            courses = root / "courses"
            courses.mkdir()
            (courses / "Bakery.tsv").write_text(
                "category\tspoken\tsingular\tplural\tmeaning_zh\nBread\tBrötchen\tdas Brötchen\tdie Brötchen\troll\n",
                encoding="utf-8",
            )
            (courses / "Breakfast.tsv").write_text(
                "category\tspoken\tsingular\tplural\tmeaning_zh\nFood\tBrötchen\tdas Brötchen\tdie Brötchen\tbread roll\n",
                encoding="utf-16",
            )
            output = root / "site"
            result = subprocess.run(
                [sys.executable, "build.py", "--courses", str(courses), "--output", str(output),
                 "--cache", str(root / "cache")],
                capture_output=True, text=True, encoding="utf-8"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("Bakery", html)
            self.assertIn("Breakfast", html)
            clips = list((output / "audio").glob("*.mp3"))
            self.assertEqual(len(clips), 1)
            self.assertEqual(clips[0].read_bytes(), Path("audio-preview/broetchen-google-translate.mp3").read_bytes())
