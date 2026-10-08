import tempfile
import unittest
from datetime import date
from pathlib import Path
import os
import subprocess
from unittest.mock import patch

from PIL import Image

from scripts import process_illustrations as processor
from scripts import generate_illustration_manifest as manifest_generator


class ProcessIllustrationsTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.illu_dir = self.root / "illu"
        self.legacy_dir = self.root / "illu legacy"
        self.illu_dir.mkdir()
        self.legacy_dir.mkdir()
        self.illu_patcher = patch.object(processor, "ILLU_DIR", self.illu_dir)
        self.legacy_patcher = patch.object(processor, "LEGACY_DIR", self.legacy_dir)
        self.root_patcher = patch.object(processor, "REPO_ROOT", self.root)
        self.illu_patcher.start()
        self.legacy_patcher.start()
        self.root_patcher.start()
        self.addCleanup(self.temporary_directory.cleanup)
        self.addCleanup(self.illu_patcher.stop)
        self.addCleanup(self.legacy_patcher.stop)
        self.addCleanup(self.root_patcher.stop)

    def make_image(self, name, image_format, size=(101, 81)):
        path = self.illu_dir / name
        Image.new("RGB", size, "red").save(path, format=image_format)
        return path

    def test_previews_keep_supported_formats_and_half_dimensions(self):
        samples = (
            ("art.jpg", "JPEG"),
            ("art.jpeg", "JPEG"),
            ("art.png", "PNG"),
            ("art.webp", "WEBP"),
            ("art.gif", "GIF"),
        )
        for name, image_format in samples:
            with self.subTest(name=name):
                source = self.make_image(name, image_format)
                preview = self.illu_dir / "preview" / name
                processor.create_preview(source, preview)
                with Image.open(preview) as image:
                    self.assertEqual(image.size, (50, 40))
                    self.assertEqual(image.format, image_format)

    def test_animated_gif_preview_keeps_all_frames(self):
        source = self.illu_dir / "animated.gif"
        frames = [Image.new("RGB", (100, 80), color) for color in ("red", "blue")]
        frames[0].save(
            source,
            save_all=True,
            append_images=frames[1:],
            duration=[100, 200],
            loop=0,
        )
        preview = self.illu_dir / "preview" / source.name

        processor.create_preview(source, preview)

        with Image.open(preview) as image:
            self.assertEqual(image.size, (50, 40))
            self.assertEqual(image.n_frames, 2)

    def test_month_anniversary_caps_at_month_end(self):
        self.assertEqual(
            processor.month_anniversary(date(2024, 1, 31)),
            date(2024, 2, 29),
        )
        self.assertEqual(
            processor.month_anniversary(date(2025, 1, 31)),
            date(2025, 2, 28),
        )

    def test_manifest_keeps_first_commit_date_after_uncommitted_move(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        image = self.make_image("moved.jpg", "JPEG")
        subprocess.run(
            ["git", "add", "illu/moved.jpg"],
            cwd=self.root,
            check=True,
        )
        environment = os.environ.copy()
        environment.update(
            GIT_AUTHOR_DATE="2024-01-15T12:00:00+00:00",
            GIT_COMMITTER_DATE="2024-01-15T12:00:00+00:00",
        )
        subprocess.run(
            ["git", "config", "user.name", "Illustration Test"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "illustration-test@example.com"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-qm", "add illustration"],
            cwd=self.root,
            env=environment,
            check=True,
        )
        legacy_image = self.legacy_dir / image.name
        image.replace(legacy_image)

        with patch.object(manifest_generator, "REPO_ROOT", self.root), patch.object(
            manifest_generator, "ILLU_DIR", self.illu_dir
        ), patch.object(manifest_generator, "LEGACY_DIR", self.legacy_dir):
            dates = manifest_generator.first_commit_dates([legacy_image])

        self.assertEqual(dates["illu legacy/moved.jpg"], "2024-01-15")

    @patch.object(processor, "first_commit_dates")
    def test_eligible_image_and_caption_move_with_preview(self, first_commit_dates):
        image = self.make_image("new.jpg", "JPEG")
        (self.illu_dir / "descriptions.txt").write_text(
            "# Keep this note\nnew.jpg | A caption\nother.jpg | Another caption\n",
            encoding="utf-8",
        )
        first_commit_dates.return_value = {
            image.relative_to(self.root).as_posix(): "2024-01-31"
        }

        processor.process_illustrations(today=date(2024, 2, 29))

        self.assertTrue((self.legacy_dir / "new.jpg").exists())
        self.assertTrue((self.legacy_dir / "preview" / "new.jpg").exists())
        self.assertIn("new.jpg | A caption", (self.legacy_dir / "descriptions.txt").read_text())
        self.assertNotIn("new.jpg | A caption", (self.illu_dir / "descriptions.txt").read_text())
        self.assertIn("# Keep this note", (self.illu_dir / "descriptions.txt").read_text())
        self.assertIn("other.jpg | Another caption", (self.illu_dir / "descriptions.txt").read_text())

    @patch.object(processor, "first_commit_dates")
    def test_recent_image_stays_in_illustrations(self, first_commit_dates):
        image = self.make_image("recent.jpg", "JPEG")
        first_commit_dates.return_value = {
            image.relative_to(self.root).as_posix(): "2024-01-31"
        }

        processor.process_illustrations(today=date(2024, 2, 28))

        self.assertTrue(image.exists())
        self.assertTrue((self.illu_dir / "preview" / image.name).exists())
        self.assertFalse((self.legacy_dir / image.name).exists())

    @patch.object(processor, "first_commit_dates")
    def test_destination_conflict_fails_without_moving_original(self, first_commit_dates):
        image = self.make_image("duplicate.jpg", "JPEG")
        Image.new("RGB", (50, 40), "blue").save(self.legacy_dir / image.name, format="JPEG")
        first_commit_dates.return_value = {
            image.relative_to(self.root).as_posix(): "2024-01-01"
        }

        with self.assertRaises(FileExistsError):
            processor.process_illustrations(today=date(2024, 2, 2))

        self.assertTrue(image.exists())


if __name__ == "__main__":
    unittest.main()
