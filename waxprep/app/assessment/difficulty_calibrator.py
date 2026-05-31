from typing import Dict, Any, List
from loguru import logger
from waxprep.app.database.client import get_db_client

class DifficultyCalibrator:
    DIFFICULTY_MIN = 1
    DIFFICULTY_MAX = 5
    CORRECT_FAST_THRESHOLD = 2
    WRONG_THRESHOLD = 3

    def __init__(self):
        self.db = get_db_client()
        self._student_difficulty_cache: Dict[str, Dict[str, int]] = {}

    async def get_current_difficulty(
        self,
        student_id: str,
        subject: str,
        concept_id: str,
    ) -> int:
        cache_key = f"{student_id}_{subject}_{concept_id}"
        if cache_key in self._student_difficulty_cache:
            return self._student_difficulty_cache[cache_key].get("difficulty", 2)

        try:
            km_response = (
                self.db.table("knowledge_maps")
                .select("mastery_score, assessment_count")
                .eq("student_id", student_id)
                .eq("concept_id", concept_id)
                .execute()
            )

            if km_response.data:
                mastery = km_response.data[0]["mastery_score"]
                count = km_response.data[0]["assessment_count"]

                if mastery >= 85:
                    difficulty = 5
                elif mastery >= 70:
                    difficulty = 4
                elif mastery >= 50:
                    difficulty = 3
                elif mastery >= 30:
                    difficulty = 2
                else:
                    difficulty = 1
            else:
                difficulty = 2

            self._student_difficulty_cache[cache_key] = {"difficulty": difficulty}
            return difficulty

        except Exception as e:
            logger.warning(f"Difficulty calibration failed: {e}")
            return 2

    async def update_after_response(
        self,
        student_id: str,
        subject: str,
        concept_id: str,
        was_correct: bool,
        score: float,
        attempts_needed: int,
    ) -> int:
        cache_key = f"{student_id}_{subject}_{concept_id}"
        current = self._student_difficulty_cache.get(cache_key, {}).get("difficulty", 2)

        if was_correct and attempts_needed == 1 and score >= 0.9:
            new_difficulty = min(self.DIFFICULTY_MAX, current + 1)
        elif was_correct and attempts_needed <= 2:
            new_difficulty = current
        elif not was_correct and attempts_needed >= 3:
            new_difficulty = max(self.DIFFICULTY_MIN, current - 1)
        else:
            new_difficulty = current

        self._student_difficulty_cache[cache_key] = {"difficulty": new_difficulty}
        return new_difficulty

    async def get_next_concept_to_assess(
        self,
        student_id: str,
        subject: str,
    ) -> str:
        try:
            response = (
                self.db.table("knowledge_maps")
                .select("concept_id, mastery_score, next_review_due_at")
                .eq("student_id", student_id)
                .eq("subject", subject)
                .order("next_review_due_at", desc=False)
                .limit(1)
                .execute()
            )

            if response.data:
                return response.data[0]["concept_id"]

            return None

        except Exception as e:
            logger.warning(f"Failed to get next concept: {e}")
            return None
