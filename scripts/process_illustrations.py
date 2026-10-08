#!/usr/bin/env python3
"""Create illustration previews and move month-old illustrations to legacy."""

import os
import tempfile
from calendar import monthrange
from datetime import date
from pathlib import Path

from PIL import Image, ImageOps, ImageSequence

from scripts.generate_illustration_manifest import first_commit_dates, list_images

REPO_ROOT = Path(__file__).resolve().parent.parent
ILLU_DIR = REPO_ROOT / "illu"
LEGACY_DIR = REPO_ROOT / "illu legacy"
PREVIEW_SCALE = 0.5


def preview_path(image_path):
    return image_path.parent / "preview" / image_path.name


def month_anniversary(committed_on):
    next_month = committed_on.month % 12 + 1
    next_year = committed_on.year + (1 if committed_on.month == 12 else 0)
    day = min(committed_on.day, monthrange(next_year, next_month)[1])
    return date(next_year, next_month, day)


def create_preview(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.name}.",
            suffix=".tmp",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        with Image.open(source) as original:
            size = (
                max(1, round(original.width * PREVIEW_SCALE)),
                max(1, round(original.height * PREVIEW_SCALE)),
            )
            icc_profile = original.info.get("icc_profile")

            if original.format == "GIF" and getattr(original, "is_animated", False):
                frames = []
                durations = []
                for frame in ImageSequence.Iterator(original):
                    frames.append(
                        frame.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
                    )
                    durations.append(
                        frame.info.get("duration", original.info.get("duration", 0))
                    )
                frames[0].save(
                    temporary_path,
                    format="GIF",
                    save_all=True,
                    append_images=frames[1:],
                    duration=durations,
                    loop=original.info.get("loop", 0),
                    disposal=2,
                )
            else:
                image = ImageOps.exif_transpose(original).resize(
                    size, Image.Resampling.LANCZOS
                )
                image_format = original.format
                if image_format == "JPEG" and image.mode not in {"RGB", "L"}:
                    image = image.convert("RGB")
                save_options = {}
                if icc_profile:
                    save_options["icc_profile"] = icc_profile
                if image_format in {"JPEG", "WEBP"}:
                    save_options.update(quality=85, optimize=True)
                elif image_format == "PNG":
                    save_options["optimize"] = True
                image.save(temporary_path, format=image_format, **save_options)

        os.replace(temporary_path, destination)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def move_description(filename):
    source = ILLU_DIR / "descriptions.txt"
    destination = LEGACY_DIR / "descriptions.txt"
    if not source.exists():
        return

    remaining = []
    moved = []
    for line in source.read_text(encoding="utf-8").splitlines():
        entry = line.strip()
        if entry and not entry.startswith("#") and "|" in entry:
            entry_filename = entry.split("|", 1)[0].strip()
            if entry_filename == filename:
                moved.append(line)
                continue
        remaining.append(line)

    if not moved:
        return

    existing = destination.read_text(encoding="utf-8").splitlines() if destination.exists() else []
    existing_names = {
        line.split("|", 1)[0].strip()
        for line in existing
        if line.strip() and not line.lstrip().startswith("#") and "|" in line
    }
    if any(line.split("|", 1)[0].strip() in existing_names for line in moved):
        raise FileExistsError(f"Legacy description already exists for {filename}")

    destination.write_text(
        "\n".join(existing + moved).rstrip() + "\n",
        encoding="utf-8",
    )
    source.write_text("\n".join(remaining).rstrip() + "\n", encoding="utf-8")


def validate_description_move(filename):
    source = ILLU_DIR / "descriptions.txt"
    destination = LEGACY_DIR / "descriptions.txt"
    if not source.exists() or not destination.exists():
        return

    source_names = {
        line.split("|", 1)[0].strip()
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "|" in line
    }
    destination_names = {
        line.split("|", 1)[0].strip()
        for line in destination.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "|" in line
    }
    if filename in source_names and filename in destination_names:
        raise FileExistsError(f"Legacy description already exists for {filename}")


def process_illustrations(today=None):
    today = today or date.today()
    new_images = list_images(ILLU_DIR)
    legacy_images = list_images(LEGACY_DIR)
    dates = first_commit_dates(new_images + legacy_images)

    for image in new_images + legacy_images:
        create_preview(image, preview_path(image))

    moved = 0
    for image in new_images:
        committed_on = date.fromisoformat(dates[image.relative_to(REPO_ROOT).as_posix()])
        if today < month_anniversary(committed_on):
            continue

        destination = LEGACY_DIR / image.name
        source_preview = preview_path(image)
        destination_preview = preview_path(destination)
        if destination.exists() or destination_preview.exists():
            raise FileExistsError(
                f"Cannot move {image.name}: a legacy image or preview already exists"
            )
        validate_description_move(image.name)

        LEGACY_DIR.mkdir(parents=True, exist_ok=True)
        destination_preview.parent.mkdir(parents=True, exist_ok=True)
        image.replace(destination)
        try:
            source_preview.replace(destination_preview)
        except OSError:
            destination.replace(image)
            raise
        move_description(image.name)
        moved += 1

    print(
        f"Generated previews for {len(new_images) + len(legacy_images)} illustration(s); "
        f"moved {moved} to legacy."
    )


if __name__ == "__main__":
    process_illustrations()
