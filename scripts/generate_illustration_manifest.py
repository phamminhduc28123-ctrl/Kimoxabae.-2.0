#!/usr/bin/env python3
"""Build the illustration feed manifest with captions and first-commit dates."""

import json
from datetime import date
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ILLU_DIR = REPO_ROOT / "illu"
LEGACY_DIR = REPO_ROOT / "illu legacy"
MANIFEST_PATH = ILLU_DIR / "manifest.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def image_order(path):
    name = path.name
    if name.startswith("illu_") and name[5:].split(".", 1)[0].isdigit():
        return 0, int(name[5:].split(".", 1)[0]), name.casefold()
    if name == "b.jpg":
        return 1, 0, name.casefold()
    if name.startswith("PXL_"):
        return 2, 0, name.casefold()
    return 3, 0, name.casefold()


def read_descriptions(directory, image_names):
    DESCRIPTIONS_PATH = directory / "descriptions.txt"
    descriptions = {}
    if not DESCRIPTIONS_PATH.exists():
        return descriptions
    for line_number, raw_line in enumerate(
        DESCRIPTIONS_PATH.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" not in line:
            raise ValueError(
                f"{DESCRIPTIONS_PATH.name}:{line_number}: expected 'filename | description'"
            )

        filename, description = line.split("|", 1)
        filename = filename.strip()
        if filename not in image_names:
            raise ValueError(
                f"{DESCRIPTIONS_PATH.name}:{line_number}: unknown illustration {filename!r}"
            )
        if filename in descriptions:
            raise ValueError(
                f"{DESCRIPTIONS_PATH.name}:{line_number}: duplicate entry for {filename!r}"
            )
        descriptions[filename] = description.strip()

    return descriptions


def first_commit_dates(image_paths):
    if not image_paths:
        return {}
    output = subprocess.run(
        [
            "git",
            "log",
            "--reverse",
            "--diff-filter=A",
            "--format=COMMIT:%cI",
            "--name-only",
            "--",
            "illu/",
            "illu legacy/",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    dates = {}
    commit_date = None
    wanted = {path.relative_to(REPO_ROOT).as_posix() for path in image_paths}
    for line in output.splitlines():
        if line.startswith("COMMIT:"):
            commit_date = line.removeprefix("COMMIT:")[:10]
        elif line in wanted and commit_date and line not in dates:
            dates[line] = commit_date

    for path in image_paths:
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        if relative_path in dates:
            continue

        history = subprocess.run(
            [
                "git",
                "log",
                "--follow",
                "--format=%cI",
                "--",
                relative_path,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        if history:
            dates[relative_path] = history[-1][:10]
        else:
            dates[relative_path] = date.today().isoformat()

    return dates


def list_images(directory):
    if not directory.is_dir():
        return []
    return sorted(
        (
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ),
        key=image_order,
    )


def main():
    groups = [(ILLU_DIR, False), (LEGACY_DIR, True)]
    all_paths = [path for directory, _ in groups for path in list_images(directory)]
    dates = first_commit_dates(all_paths)

    illustrations = []
    for directory, legacy in groups:
        paths = list_images(directory)
        descriptions = read_descriptions(directory, {path.name for path in paths})
        for order, path in enumerate(paths):
            relative_path = path.relative_to(REPO_ROOT).as_posix()
            illustrations.append(
                {
                    "id": path.stem,
                    "file": relative_path,
                    "date": dates[relative_path],
                    "description": descriptions.get(path.name, ""),
                    "legacy": legacy,
                    "order": order,
                }
            )

    ILLU_DIR.mkdir(exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(illustrations, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(illustrations)} illustration(s) to {MANIFEST_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
