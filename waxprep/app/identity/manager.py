from typing import Optional, Dict, Any
from datetime import datetime
from loguru import logger
from waxprep.app.core.constants import Platform, StudentStatus
from waxprep.app.core.exceptions import StudentNotFoundError, DatabaseError
from waxprep.app.identity.wax_code import generate_wax_code
from waxprep.app.database.client import get_db_client


class IdentityManager:

    def __init__(self):
        self.db = get_db_client()

    async def get_or_create_student(
        self,
        platform: Platform,
        platform_user_id: str,
    ) -> Dict[str, Any]:
        try:
            student = await self._find_student_by_platform(platform, platform_user_id)

            if student:
                await self._update_last_active(student["id"])
                logger.debug(f"Returning student: {student['wax_code']}")
                return student

            wax_code = generate_wax_code(platform, platform_user_id if platform == Platform.WHATSAPP else None)

            student_data = {
                "wax_code": wax_code,
                "status": StudentStatus.ACTIVE.value,
                "last_active_at": datetime.utcnow().isoformat(),
            }

            if platform == Platform.WHATSAPP:
                student_data["platform_whatsapp"] = platform_user_id
            else:
                student_data["platform_telegram"] = platform_user_id

            response = self.db.table("students").insert(student_data).execute()

            if not response.data:
                raise DatabaseError("Failed to create student record")

            new_student = response.data[0]

            await self._create_student_profile(new_student["id"])

            logger.info(f"New student created: {new_student['wax_code']} on {platform.value}")
            return new_student

        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error in get_or_create_student: {e}")
            raise DatabaseError(f"Identity system error: {str(e)}")

    async def _find_student_by_platform(
        self,
        platform: Platform,
        platform_user_id: str
    ) -> Optional[Dict[str, Any]]:
        try:
            if platform == Platform.WHATSAPP:
                response = (
                    self.db.table("students")
                    .select("*")
                    .eq("platform_whatsapp", platform_user_id)
                    .execute()
                )
            else:
                response = (
                    self.db.table("students")
                    .select("*")
                    .eq("platform_telegram", platform_user_id)
                    .execute()
                )

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error finding student: {e}")
            return None

    async def _update_last_active(self, student_id: str) -> None:
        try:
            self.db.table("students").update({
                "last_active_at": datetime.utcnow().isoformat()
            }).eq("id", student_id).execute()
        except Exception as e:
            logger.warning(f"Failed to update last_active for {student_id}: {e}")

    async def _create_student_profile(self, student_id: str) -> None:
        try:
            self.db.table("student_profiles").insert({
                "student_id": student_id,
            }).execute()
        except Exception as e:
            logger.error(f"Failed to create profile for {student_id}: {e}")

    async def get_student_profile(self, student_id: str) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.db.table("student_profiles")
                .select("*")
                .eq("student_id", student_id)
                .execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting profile for {student_id}: {e}")
            return None

    async def update_student_profile(self, student_id: str, updates: Dict[str, Any]) -> None:
        try:
            self.db.table("student_profiles").update(updates).eq("student_id", student_id).execute()
        except Exception as e:
            logger.error(f"Error updating profile for {student_id}: {e}")

    async def update_student(self, student_id: str, updates: Dict[str, Any]) -> None:
        try:
            self.db.table("students").update(updates).eq("id", student_id).execute()
        except Exception as e:
            logger.error(f"Error updating student {student_id}: {e}")

    async def increment_message_counts(self, student_id: str, direction: str) -> None:
        try:
            if direction == "inbound":
                self.db.rpc("increment_messages_received", {"student_id_param": student_id}).execute()
            else:
                self.db.rpc("increment_messages_sent", {"student_id_param": student_id}).execute()
        except Exception as e:
            logger.warning(f"Failed to increment message count: {e}")
