#!/usr/bin/env python3
"""
Scans /blog for article HTML files, pairs each with its thumbnail in /blog/Thumbnail,
pulls a title/subtitle out of the article text, and records the date it was first
committed to git. Writes the result to blog/manifest.json for the blog pages to fetch.
"""

import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = REPO_ROOT / "blog"
THUMB_DIR = BLOG_DIR / "Thumbnail"
MANIFEST_PATH = BLOG_DIR / "manifest.json"

IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp", ".gif"]


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "article"


def to_posix(path):
    return path.relative_to(REPO_ROOT).as_posix()


def find_thumbnail(base_name):
    for ext in IMAGE_EXTENSIONS:
        candidate = THUMB_DIR / f"{base_name}{ext}"
        if candidate.exists():
            return to_posix(candidate)
    return None


def extract_text(html):
    text = re.sub(r"<[^>]+>", " ", html)
    text = (text.replace("&nbsp;", " ")
                .replace("&mdash;", "\u2014")
                .replace("&quot;", '"')
                .replace("&#39;", "'")
                .replace("&amp;", "&"))
    return re.sub(r"\s+", " ", text).strip()


def extract_title_and_subtitle(html):
    body_match = re.search(r"<body[\s\S]*?</body>", html, re.IGNORECASE)
    body = body_match.group(0) if body_match else html

    heading_match = re.search(r"<h[1-3][^>]*>([\s\S]*?)</h[1-3]>", body, re.IGNORECASE)
    title = extract_text(heading_match.group(1)) if heading_match else "Untitled"

    after_heading = body[heading_match.end():] if heading_match else body
    paragraph_match = re.search(r"<p[^>]*>([\s\S]*?)</p>", after_heading, re.IGNORECASE)
    subtitle = extract_text(paragraph_match.group(1)) if paragraph_match else ""

    if len(subtitle) > 140:
        subtitle = f"{subtitle[:137].strip()}..."

    return title, subtitle


def get_first_commit_date(relative_path):
    for args in (
        ["git", "log", "--follow", "--diff-filter=A", "--format=%aI", "--", relative_path],
        ["git", "log", "--follow", "--format=%aI", "--", relative_path],
    ):
        try:
            output = subprocess.run(
                args, cwd=REPO_ROOT, capture_output=True, text=True, check=True
            ).stdout.strip()
        except subprocess.CalledProcessError:
            continue

        if output:
            return output.splitlines()[-1]

    return None


def main():
    html_files = sorted(p for p in BLOG_DIR.glob("*.html"))

    articles = []
    for file_path in html_files:
        base_name = file_path.stem
        html = file_path.read_text(encoding="utf-8")
        title, subtitle = extract_title_and_subtitle(html)
        relative_file = to_posix(file_path)

        articles.append({
            "slug": slugify(base_name),
            "title": title,
            "subtitle": subtitle,
            "file": relative_file,
            "thumbnail": find_thumbnail(base_name),
            "date": get_first_commit_date(relative_file),
        })

    MANIFEST_PATH.write_text(json.dumps(articles, indent="\t") + "\n", encoding="utf-8")
    print(f"Wrote {len(articles)} article(s) to {to_posix(MANIFEST_PATH)}")


if __name__ == "__main__":
    main()
