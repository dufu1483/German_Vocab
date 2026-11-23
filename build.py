import argparse
import csv
import hashlib
import io
import json
import shutil
import tempfile
import time
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIELDS = ["category", "spoken", "singular", "plural", "meaning_zh"]


def answer_forms(value):
    return [form.strip() for form in value.split("|") if form.strip()]


def normalized(value):
    return ' '.join(unicodedata.normalize('NFC', value).split())


def validate_articles(answers, articles, column, location):
    for answer in answers:
        parts = answer.split(maxsplit=1)
        if len(parts) != 2 or parts[0] not in articles:
            raise ValueError(f'{location}: {column} answer {answer!r} must start with '
                             f'{", ".join(articles)} followed by a noun')


def numbered_tsv_rows(path):
    raw = path.read_bytes()
    encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    try:
        decoded = raw.decode(encoding)
    except UnicodeDecodeError as error:
        raise ValueError(f'{path.name}: invalid text encoding: {error.reason}') from error
    rows = csv.reader(io.StringIO(decoded, newline=''), delimiter='\t', strict=True)
    while True:
        number = rows.line_num + 1
        try:
            row = next(rows)
        except StopIteration:
            return
        except csv.Error as error:
            raise ValueError(f'{path.name}:{number}: invalid TSV: {error}') from error
        yield number, row


def read_courses(folder):
    courses = []
    for path in sorted(folder.glob("*.tsv")):
        rows = numbered_tsv_rows(path)
        if next(rows, None) != (1, FIELDS):
            raise ValueError(f"{path.name}:1: expected headers {', '.join(FIELDS)}")
        words = []
        seen = {}
        for number, row in rows:
            if not any(row):
                continue
            if len(row) != 5:
                raise ValueError(f"{path.name}:{number}: expected five columns")
            category, spoken, singular, plural, meaning = map(str.strip, row)
            singular_forms = answer_forms(singular)
            plural_forms = answer_forms(plural)
            if not category or not spoken or not (singular_forms or plural_forms):
                raise ValueError(f"{path.name}:{number}: category, spoken text and an answer are required")
            location = f'{path.name}:{number}'
            validate_articles(singular_forms, ('der', 'die', 'das'), 'singular', location)
            validate_articles(plural_forms, ('die',), 'plural', location)
            identity = (normalized(category), normalized(spoken),
                        frozenset(map(normalized, singular_forms)),
                        frozenset(map(normalized, plural_forms)), normalized(meaning))
            if identity in seen:
                raise ValueError(f'{location}: duplicate entry (first listed on line {seen[identity]})')
            seen[identity] = number
            key = hashlib.sha256(f"gTTS-2.5.4/de/com/normal/{spoken}".encode()).hexdigest()
            words.append(dict(category=category, spoken=spoken, singular=singular_forms,
                              plural=plural_forms, meaning=meaning, audio=f"audio/{key}.mp3"))
        if not words:
            raise ValueError(f"{path.name}: no words")
        courses.append(dict(title=path.stem, words=words))
    if not courses:
        raise ValueError(f"{folder}: no courses")
    return courses


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--courses", type=Path, default=ROOT / "courses")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--cache", type=Path, default=ROOT / ".tts-cache")
    parser.add_argument("--audio-store", type=Path, help="Directory containing previously archived MP3s")
    args = parser.parse_args()
    try:
        courses = read_courses(args.courses)
        build(courses, args.output, args.cache, args.audio_store)
    except (ValueError, OSError) as error:
        parser.exit(1, f"{error}\n")


def build(courses, output, cache, audio_store):
    cache.mkdir(parents=True, exist_ok=True)
    clips = {}
    for course in courses:
        for word in course['words']:
            relative = Path(word['audio'])
            name = relative.name
            if name in clips:
                continue
            clip = cache / name
            sources = [ROOT / 'dist' / relative, clip]
            if audio_store is not None:
                sources.insert(0, audio_store / name)
            for source in sources:
                if source.is_file() and source.stat().st_size:
                    clips[name] = source
                    break
            else:
                synthesize(word['spoken'], clip, course['title'])
                clips[name] = clip

    data = json.dumps(courses, ensure_ascii=False).replace('<', r'\u003c')
    html = (ROOT / 'template.html').read_text(encoding='utf-8-sig').replace('<!-- COURSE_DATA -->', f'<script type="application/json" id="courses">{data}</script>')
    (output / 'audio').mkdir(parents=True, exist_ok=True)
    for name, source in clips.items():
        destination = output / 'audio' / name
        if source.resolve() != destination.resolve():
            shutil.copyfile(source, destination)
    (output / 'index.html').write_text(html, encoding='utf-8')


def synthesize(text, destination, title):
    from gtts import gTTS, gTTSError

    with tempfile.TemporaryDirectory(dir=destination.parent) as folder:
        temporary = Path(folder) / 'clip.mp3'
        for attempt in range(3):
            try:
                gTTS(text, lang='de', tld='com', timeout=20).save(str(temporary))
                if not temporary.stat().st_size:
                    raise ValueError('empty MP3')
                temporary.replace(destination)
                return
            except (gTTSError, ValueError) as error:
                if attempt == 2:
                    raise ValueError(f'{title} / {text}: {error}') from error
                time.sleep(attempt + 1)


if __name__ == "__main__":
    main()
