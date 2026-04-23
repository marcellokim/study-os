import unittest

from study_os.core.constants import ErrorCode, StudyStatus
from study_os.core.models import CourseConfig, MasteryRecord, ReviewedItemUpdate


class ModelsTest(unittest.TestCase):
    def test_state_order_is_stable(self) -> None:
        self.assertEqual(
            [status.value for status in StudyStatus],
            ["NEW", "LEARNED", "R0", "R1", "R2", "FINAL", "MASTERED"],
        )

    def test_reviewed_item_defaults_are_conservative(self) -> None:
        update = ReviewedItemUpdate(item_id="include_vs_extend", phase="review", result="wrong")
        self.assertEqual(update.confidence, "unknown")
        self.assertIsNone(update.error_code)

    def test_mastery_record_defaults_to_new(self) -> None:
        record = MasteryRecord(item_id="include_vs_extend", block_id="use_case_diagram")
        self.assertEqual(record.status, "NEW")
        self.assertEqual(record.last_result, "uncertain")

    def test_course_config_keeps_exam_date(self) -> None:
        course = CourseConfig(
            course_slug="operating-systems-midterm",
            course_name="Operating Systems Midterm",
            exam_date="2026-05-20",
            timezone="Asia/Seoul",
        )
        self.assertEqual(course.exam_date, "2026-05-20")
        self.assertEqual(ErrorCode.C8.value, "C8")
