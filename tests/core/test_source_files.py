from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from study_os.core.models import SourceLink, VisualRequirement
from study_os.core.source_files import validate_source_files
from study_os.core.validation import ValidationError


class SourceFileValidationTest(unittest.TestCase):
    def test_accepts_real_pdf_and_text_source_files(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            pdf_path = workspace / "courses/os-midterm/sources/syllabus/syllabus.pdf"
            txt_path = workspace / "courses/os-midterm/sources/transcripts/week01.txt"
            pdf_path.parent.mkdir(parents=True)
            txt_path.parent.mkdir(parents=True)
            pdf_path.write_bytes(b"%PDF-1.4\n% sample pdf bytes\n")
            txt_path.write_text("lecture transcript\n", encoding="utf-8")

            validate_source_files(
                workspace,
                [
                    SourceLink(
                        block_id="source_inventory",
                        source_type="syllabus",
                        path="courses/os-midterm/sources/syllabus/syllabus.pdf",
                    ),
                    SourceLink(
                        block_id="source_inventory",
                        source_type="transcript",
                        path="courses/os-midterm/sources/transcripts/week01.txt",
                    ),
                ],
                [],
            )

    def test_rejects_missing_manifest_source_file(self) -> None:
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValidationError, "source file not found"):
                validate_source_files(
                    Path(tmp),
                    [
                        SourceLink(
                            block_id="source_inventory",
                            source_type="syllabus",
                            path="courses/os-midterm/sources/syllabus/missing.pdf",
                        )
                    ],
                    [],
                )

    def test_rejects_invalid_pdf_magic(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            pdf_path = workspace / "courses/os-midterm/sources/slides/week01.pdf"
            pdf_path.parent.mkdir(parents=True)
            pdf_path.write_text("not a pdf", encoding="utf-8")

            with self.assertRaisesRegex(ValidationError, "does not look like a PDF"):
                validate_source_files(
                    workspace,
                    [
                        SourceLink(
                            block_id="source_inventory",
                            source_type="slides",
                            path="courses/os-midterm/sources/slides/week01.pdf",
                        )
                    ],
                    [],
                )

    def test_rejects_source_paths_outside_workspace(self) -> None:
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValidationError, "must stay within the workspace"):
                validate_source_files(
                    Path(tmp),
                    [
                        SourceLink(
                            block_id="source_inventory",
                            source_type="syllabus",
                            path="../secret.pdf",
                        )
                    ],
                    [],
                )

    def test_requires_available_visual_file_but_allows_missing_visual_placeholder(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            image_path = workspace / "courses/os-midterm/sources/images/diagram.svg"
            image_path.parent.mkdir(parents=True)
            image_path.write_text("<svg></svg>\n", encoding="utf-8")

            validate_source_files(
                workspace,
                [],
                [
                    VisualRequirement(
                        item_id="diagram_axis",
                        block_id="source_inventory",
                        description="Need the real diagram.",
                        required_image="courses/os-midterm/sources/images/diagram.svg",
                        status="available",
                    ),
                    VisualRequirement(
                        item_id="missing_diagram",
                        block_id="source_inventory",
                        description="Still needs extraction.",
                        required_image="courses/os-midterm/sources/images/missing.png",
                        status="missing",
                    ),
                ],
            )
