import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from waxprep.app.gateways.normalizer import NormalizedMessage
from waxprep.app.identity.manager import IdentityManager
from waxprep.app.conversation.history_manager import ConversationHistoryManager
from waxprep.app.ai.engine import WaxPrepAIEngine
from waxprep.app.ai.prompts import build_teaching_prompt, build_knowledge_map_summary, build_assessment_feedback_prompt
from waxprep.app.core.constants import Platform, MessageDirection, MessageType, Intent
from waxprep.app.database.client import get_db_client
from waxprep.app.cache.dedup_cache import DeduplicationCache
from waxprep.app.cache.student_cache import StudentCache
from waxprep.app.memory.event_logger import LearningEventLogger
from waxprep.app.memory.artifact_writer import MemoryArtifactWriter
from waxprep.app.memory.session_summary import SessionSummaryGenerator
from waxprep.app.memory.spaced_repetition import SpacedRepetitionEngine
from waxprep.app.ai.profile_extractor import ProfileIntelligenceExtractor
from waxprep.app.assessment.engine import AssessmentEngine
from waxprep.app.assessment.worked_problem_engine import WorkedProblemEngine
from waxprep.app.assessment.difficulty_calibrator import DifficultyCalibrator
from waxprep.app.assessment.jamb_simulator import JAMBSimulator
from waxprep.app.assessment.waec_simulator import WAECSimulator
from waxprep.app.assessment.exam_countdown import ExamCountdownManager
from waxprep.app.ai.subject_router import get_teaching_intelligence, should_suggest_assessment
from waxprep.app.ai.subject_detector import detect_subject_and_topic, is_topic_switch_intent
from waxprep.app.ai.frustration_detector import FrustrationDetector
from waxprep.app.ai.language_bridge import LanguageBridge
from waxprep.app.ai.scholarship_advisor import ScholarshipAdvisor
from waxprep.app.ai.career_guidance import CareerGuidanceEngine
from waxprep.app.ai.study_plan_generator import StudyPlanGenerator
from waxprep.app.gamification.achievement_engine import AchievementEngine
from waxprep.app.gamification.referral_system import ReferralSystem
from waxprep.app.subscriptions.manager import SubscriptionManager
from waxprep.app.core.content_safety import ContentSafetyFilter
from waxprep.app.core.time_awareness import get_time_context_string, get_session_gap_context, format_exam_countdown
from waxprep.app.curriculum.post_utme.preparation_guide import is_post_utme_request, get_university_profile, generate_post_utme_advice

identity_manager = IdentityManager()
history_manager = ConversationHistoryManager()
ai_engine = WaxPrepAIEngine()
event_logger = LearningEventLogger()
artifact_writer = MemoryArtifactWriter()
session_summary_generator = SessionSummaryGenerator()
spaced_rep_engine = SpacedRepetitionEngine()
profile_extractor = ProfileIntelligenceExtractor()
assessment_engine = AssessmentEngine()
worked_problem_engine = WorkedProblemEngine()
difficulty_calibrator = DifficultyCalibrator()
jamb_simulator = JAMBSimulator()
waec_simulator = WAECSimulator()
exam_countdown = ExamCountdownManager()
frustration_detector = FrustrationDetector()
language_bridge = LanguageBridge()
scholarship_advisor = ScholarshipAdvisor()
career_engine = CareerGuidanceEngine()
study_plan_generator = StudyPlanGenerator()
achievement_engine = AchievementEngine()
referral_system = ReferralSystem()
subscription_manager = SubscriptionManager()
content_safety = ContentSafetyFilter()
student_cache = StudentCache()
dedup_cache = DeduplicationCache()
_message_counts_since_assessment: Dict[str, int] = {}

async def dispatch_message(normalized_message: NormalizedMessage) -> None:
    try:
        if await dedup_cache.is_duplicate(normalized_message.platform_message_id):
            return
        await dedup_cache.mark_processed(normalized_message.platform_message_id)
        if normalized_message.is_empty:
            return

        is_safe, safety_flag, safety_response = content_safety.check_message(normalized_message.content)
        if safety_response:
            await _send_response(normalized_message.platform, normalized_message.platform_user_id, safety_response)
        if not is_safe:
            return

        if normalized_message.is_voice and normalized_message.media_url:
            try:
                from waxprep.app.gateways.whatsapp.voice_transcriber import VoiceTranscriber
                transcribed = await VoiceTranscriber().transcribe_whatsapp_audio(normalized_message.media_url)
                if transcribed and len(transcribed) > 3:
                    normalized_message.content = transcribed
                    normalized_message.is_voice = False
                    logger.info(f"Voice transcribed: {transcribed[:60]}")
                else:
                    normalized_message.content = "I sent a voice note."
            except Exception as e:
                logger.warning(f"Voice transcription error: {e}")
                normalized_message.content = "I sent a voice note."

        student = await identity_manager.get_or_create_student(
            platform=normalized_message.platform,
            platform_user_id=normalized_message.platform_user_id,
        )

        allowed, limit_message = await subscription_manager.check_message_allowance(student["id"])
        if not allowed:
            await _send_response(normalized_message.platform, normalized_message.platform_user_id, limit_message)
            return
        await subscription_manager.increment_daily_count(student["id"])

        is_returning = student.get("session_count", 0) > 0
        is_new_session = await _is_new_session(student["id"], normalized_message.platform.value)

        if is_new_session:
            db = get_db_client()
            db.table("students").update({"session_count": (student.get("session_count") or 0) + 1}).eq("id", student["id"]).execute()

        conversation = await history_manager.get_or_create_active_conversation(
            student_id=student["id"], platform=normalized_message.platform.value,
        )
        await history_manager.save_message(
            conversation_id=conversation["id"], student_id=student["id"],
            direction=MessageDirection.INBOUND.value, content=normalized_message.content,
            message_type=normalized_message.message_type, platform_message_id=normalized_message.platform_message_id,
        )
        await _mark_as_read(normalized_message)

        conversation_history = await history_manager.get_conversation_history_for_ai(conversation_id=conversation["id"], limit=15)
        recent_context = " | ".join([m["content"][:60] for m in conversation_history[-3:] if m["role"] == "user"]) if conversation_history else ""

        intent = await ai_engine.classify_intent(message=normalized_message.content, recent_context=recent_context)

        student_profile_data = await student_cache.get_student_profile(student["id"])
        merged_student_data = {**student}
        if student_profile_data: merged_student_data["profile"] = student_profile_data

        detected_subject, detected_topic = detect_subject_and_topic(normalized_message.content)
        current_subject = student_profile_data.get("current_subject") if student_profile_data else None
        current_topic = student_profile_data.get("current_topic") if student_profile_data else None

        profile_updates = {}
        if detected_subject and detected_subject != current_subject:
            profile_updates["current_subject"] = detected_subject
            current_subject = detected_subject
        if detected_topic and detected_topic != current_topic:
            profile_updates["current_topic"] = detected_topic
            current_topic = detected_topic
        if profile_updates:
            await student_cache.update_student_profile(student["id"], profile_updates)
            if student_profile_data: student_profile_data.update(profile_updates)

        frustration_analysis = frustration_detector.analyze_message(student_id=student["id"], message=normalized_message.content, intent=intent)
        frustration_instruction = frustration_detector.get_strategy_instruction(frustration_analysis=frustration_analysis, current_topic=current_topic or "current topic")

        student_name = student_profile_data.get("student_name", "there") if student_profile_data else "there"
        msg_lower = normalized_message.content.lower()

        # Language bridge
        requested_language = language_bridge.detect_language_request(normalized_message.content)
        if requested_language:
            bridge_response = await language_bridge.provide_language_bridge(concept=current_topic or normalized_message.content[:50], language=requested_language, subject=current_subject or "general", class_level=student.get("inferred_class_level", "SS1"))
            await _deliver_and_log(normalized_message, student, conversation, bridge_response, intent, "language_bridge")
            return

        # Scholarship & Admission
        if scholarship_advisor.is_scholarship_request(normalized_message.content):
            response = await scholarship_advisor.get_relevant_scholarships(student_id=student["id"], class_level=student.get("inferred_class_level", "SS3"), exam_target=student.get("primary_exam_target"))
            await _deliver_and_log(normalized_message, student, conversation, response, intent, "scholarship")
            return
        if scholarship_advisor.is_admission_request(normalized_message.content):
            response = await scholarship_advisor.get_admission_guidance(message=normalized_message.content, student_id=student["id"])
            await _deliver_and_log(normalized_message, student, conversation, response, intent, "admission_guidance")
            return

        # Post-UTME
        if is_post_utme_request(normalized_message.content):
            university = get_university_profile(normalized_message.content)
            response = generate_post_utme_advice(university, student_profile_data or {})
            await _deliver_and_log(normalized_message, student, conversation, response, intent, "post_utme")
            return

        # Career guidance
        if career_engine.is_career_request(normalized_message.content):
            response = await career_engine.provide_career_guidance(message=normalized_message.content, student_id=student["id"])
            await _deliver_and_log(normalized_message, student, conversation, response, intent, "career_guidance")
            return

        # Study plan
        if study_plan_generator.is_study_plan_request(normalized_message.content):
            plan = await study_plan_generator.generate_study_plan(student_id=student["id"], exam=student.get("primary_exam_target", "JAMB"), exam_date=student.get("exam_date"))
            await _deliver_and_log(normalized_message, student, conversation, plan, intent, "study_plan")
            return

        # Progress check
        if intent in ["progress_check", "PROGRESS_CHECK"]:
            xp_status = await achievement_engine.get_student_xp_status(student["id"])
            achievement_summary = await achievement_engine.get_student_achievements_summary(student["id"])
            knowledge_items = await student_cache.get_knowledge_map(student["id"])
            mastered = sum(1 for k in knowledge_items if k["mastery_score"] >= 70)
            name_part = f"{student_name}, " if student_name != "there" else ""
            progress_text = f"{name_part}here is where you stand right now:\n\n{achievement_summary}\n\nKnowledge Map: {mastered} concepts mastered out of {len(knowledge_items)} covered\nSessions completed: {student.get('session_count', 0)}\n\nWhat do you want to focus on today?"
            await _deliver_and_log(normalized_message, student, conversation, progress_text, intent, "progress")
            return

        # Referral
        if referral_system.is_referral_request(normalized_message.content):
            referral_code = await referral_system.get_or_create_referral_code(student["id"], student_name)
            referral_stats = await referral_system.get_referral_stats(student["id"])
            ref_message = f"Your WaxPrep referral code: *{referral_code}*\n\nShare it with friends. Every friend who joins earns you 7 free days of Basic plan plus 200 XP. They also get 100 bonus XP.\n\nTotal referrals: {referral_stats.get('total_referrals', 0)}\nFree days earned: {referral_stats.get('premium_days_earned', 0)}\n\nCopy: 'Join me on WaxPrep — the AI tutor that actually knows you. Use code {referral_code} at waxprep.ng'"
            await _deliver_and_log(normalized_message, student, conversation, ref_message, intent, "referral")
            return

        msg_upper = normalized_message.content.strip().upper()

        # WAEC Simulator
        if waec_simulator.has_active_session(student["id"]):
            session_type = waec_simulator.get_session_type(student["id"])
            if session_type == "objective" and waec_simulator.is_simulation_answer(normalized_message.content):
                waec_response = await waec_simulator.process_objective_answer(student["id"], normalized_message.content)
                if waec_response:
                    await _deliver_and_log(normalized_message, student, conversation, waec_response, intent, "waec_sim")
                    return
            elif session_type == "theory" and len(normalized_message.content) > 20:
                waec_response = await waec_simulator.process_theory_answer(student["id"], normalized_message.content)
                if waec_response:
                    await _deliver_and_log(normalized_message, student, conversation, waec_response, intent, "waec_theory")
                    return

        waec_triggers = ["waec practice", "waec questions", "waec simulation", "waec mock", "past waec", "waec objective", "waec theory", "practice waec", "do waec", "lets do waec"]
        if any(t in msg_lower for t in waec_triggers):
            can_use = await subscription_manager.can_use_feature(student["id"], "waec_practice")
            if not can_use:
                await _deliver_and_log(normalized_message, student, conversation, await subscription_manager.get_upgrade_message("waec_practice"), intent, "upgrade_prompt")
                return
            subject_for_waec = current_subject or "biology"
            if "theory" in msg_lower:
                waec_start = await waec_simulator.start_theory_session(student["id"], subject_for_waec, student_name)
            else:
                waec_start = await waec_simulator.start_objective_session(student["id"], subject_for_waec, student_name=student_name, count=10)
            await _deliver_and_log(normalized_message, student, conversation, waec_start, intent, "waec_start")
            return

        # JAMB Simulator
        if jamb_simulator.has_active_simulation(student["id"]) and msg_upper in ["A", "B", "C", "D"]:
            jamb_response = await jamb_simulator.process_answer(student["id"], normalized_message.content)
            if jamb_response:
                await _deliver_and_log(normalized_message, student, conversation, jamb_response, intent, "jamb_sim")
                return

        jamb_triggers = ["jamb practice", "practice jamb", "jamb simulation", "mock jamb", "do some questions", "past questions", "jamb questions"]
        if any(t in msg_lower for t in jamb_triggers):
            can_use = await subscription_manager.can_use_feature(student["id"], "jamb_practice")
            if not can_use:
                await _deliver_and_log(normalized_message, student, conversation, await subscription_manager.get_upgrade_message("jamb_practice"), intent, "upgrade_prompt")
                return
            exam_subjects = [current_subject] if current_subject else ["biology", "mathematics", "physics", "chemistry", "english_language"]
            sim_response = await jamb_simulator.start_simulation(student_id=student["id"], subjects=exam_subjects[:3], questions_per_subject=3, student_name=student_name)
            await _deliver_and_log(normalized_message, student, conversation, sim_response, intent, "jamb_sim_start")
            return

        # Worked Problem Engine
        if worked_problem_engine.has_active_problem(student["id"]):
            wp_response = await worked_problem_engine.process_step_response(student_id=student["id"], student_response=normalized_message.content)
            if wp_response:
                await _deliver_and_log(normalized_message, student, conversation, wp_response, intent, "worked_problem")
                frustration_detector.record_success(student["id"])
                return

        # Assessment Engine
        if assessment_engine.has_active_assessment(student["id"]):
            evaluation = await assessment_engine.evaluate_answer(student_id=student["id"], student_answer=normalized_message.content)
            if evaluation:
                feedback_prompt = build_assessment_feedback_prompt(question=evaluation.get("question", ""), student_answer=normalized_message.content, correct_answer=evaluation.get("correct_answer", ""), subject=evaluation.get("subject", current_subject or ""), concept=evaluation.get("concept", ""), attempts=evaluation.get("attempts", 1))
                response_text = await ai_engine.generate_from_single_prompt(feedback_prompt)
                if response_text:
                    response_text = content_safety.filter_response(response_text)
                    await _deliver_and_log(normalized_message, student, conversation, response_text, intent, "assessment_feedback")
                    if evaluation.get("is_correct"):
                        frustration_detector.record_success(student["id"])
                        asyncio.create_task(_check_achievements_async(student_id=student["id"], event_type="assessment_correct", event_data={"concept": evaluation.get("concept", "")}, student_name=student_name, platform=normalized_message.platform, platform_user_id=normalized_message.platform_user_id))
                    return

        # Build teaching prompt
        memory_context = await artifact_writer.build_memory_context_string(student["id"])
        knowledge_map_items = await student_cache.get_knowledge_map(student["id"])
        knowledge_map_summary_text = build_knowledge_map_summary(knowledge_map_items)
        active_misconceptions = await _get_active_misconceptions(student["id"])

        previous_session_summary = None
        return_greeting = None
        if is_new_session and is_returning:
            previous_session_summary = await history_manager.get_previous_session_summary(student["id"])
            if previous_session_summary:
                return_greeting = await session_summary_generator.generate_return_greeting(student["id"])

        subject_intelligence = ""
        if current_subject or current_topic:
            subject_intelligence = await get_teaching_intelligence(subject=current_subject or "", topic=current_topic or "", class_level=student.get("inferred_class_level", "SS1"), misconceptions=[m.get("description", "") for m in active_misconceptions])

        time_context = get_time_context_string()
        gap_context = get_session_gap_context(student.get("last_active_at"))
        exam_context = format_exam_countdown(student.get("exam_date"))
        current_datetime_context = time_context + (" " + gap_context if gap_context else "") + (" " + exam_context if exam_context else "")

        assessment_context = None
        if frustration_analysis.get("frustration_level", 0) < 2:
            student_msg_key = student["id"]
            _message_counts_since_assessment[student_msg_key] = _message_counts_since_assessment.get(student_msg_key, 0) + 1
            should_assess = await should_suggest_assessment(subject=current_subject or "", topic=current_topic or "", message_count_since_last_assessment=_message_counts_since_assessment.get(student_msg_key, 0))
            if should_assess and current_subject and current_topic:
                _message_counts_since_assessment[student_msg_key] = 0
                misconception_descriptions = [m.get("description", "") for m in active_misconceptions if m.get("status") == "active"]
                difficulty = await difficulty_calibrator.get_current_difficulty(student_id=student["id"], subject=current_subject, concept_id=current_topic.lower().replace(" ", "_"))
                question_data = await assessment_engine.generate_question(student_id=student["id"], subject=current_subject, concept=current_topic, class_level=student.get("inferred_class_level", "SS1"), difficulty=difficulty, misconceptions=misconception_descriptions, recent_context=recent_context)
                if question_data:
                    assessment_context = {"current_question": question_data["question"], "correct_answer": question_data["correct_answer"], "difficulty_level": difficulty, "attempts": 0}

        system_prompt, messages = build_teaching_prompt(
            student_profile=merged_student_data, conversation_history=conversation_history[:-1],
            current_message=normalized_message.content, session_state=conversation.get("session_state", "onboarding"),
            previous_session_summary=previous_session_summary, active_misconceptions=active_misconceptions,
            current_topic=current_topic, current_subject=current_subject,
            memory_context=memory_context if memory_context else None,
            knowledge_map_summary=knowledge_map_summary_text if knowledge_map_summary_text else None,
            is_returning_student=is_new_session and is_returning and bool(previous_session_summary),
            return_greeting=return_greeting, assessment_context=assessment_context,
            subject_intelligence=subject_intelligence if subject_intelligence else None,
            frustration_instruction=frustration_instruction if frustration_instruction else None,
            current_datetime=current_datetime_context,
        )

        ai_result = await ai_engine.generate_teaching_response_from_prompt(system_prompt=system_prompt, messages=messages)
        response_text = content_safety.filter_response(ai_result["response"])
        model_used = ai_result.get("model_used", "unknown")

        await _deliver_and_log(normalized_message, student, conversation, response_text, intent, model_used, student_profile_data)

        if len(conversation_history) % 5 == 0 or len(conversation_history) <= 3:
            asyncio.create_task(profile_extractor.extract_and_update(student_id=student["id"], conversation_history=conversation_history))

        await _detect_and_store_emotional_context(student_id=student["id"], session_id=conversation["id"], intent=intent, message=normalized_message.content)
        await _update_student_from_interaction(student_id=student["id"], student=student, conversation_id=conversation["id"], intent=intent, message_content=normalized_message.content)

        if is_new_session:
            await event_logger.log_session_started(student_id=student["id"], session_id=conversation["id"], is_returning=is_returning, days_since_last=await _days_since_last_session(student["id"]))
            asyncio.create_task(_check_achievements_async(student_id=student["id"], event_type="session_started", event_data={"session_count": student.get("session_count", 0), "days_since_last": await _days_since_last_session(student["id"])}, student_name=student_name, platform=normalized_message.platform, platform_user_id=normalized_message.platform_user_id))

        logger.info(f"OK: {student['wax_code']} | {intent} | {model_used} | {ai_result.get('processing_time_ms', 0)}ms | frus:{frustration_analysis.get('frustration_level', 0)}")

    except Exception as e:
        logger.error(f"Dispatch error: {e}", exc_info=True)
        await _send_error_response(normalized_message)

async def _deliver_and_log(normalized_message, student, conversation, response_text, intent, model_used, student_profile_data=None):
    await _send_response(platform=normalized_message.platform, platform_user_id=normalized_message.platform_user_id, response_text=response_text)
    if normalized_message.platform == Platform.WHATSAPP and student_profile_data and len(response_text) > 100:
        prefs = student_profile_data if isinstance(student_profile_data, dict) else {}
        if prefs.get("voice_preferred") is True or normalized_message.is_voice:
            can_voice = await subscription_manager.can_use_feature(student["id"], "voice_responses")
            if can_voice:
                from waxprep.app.gateways.tts.voice_generator import VoiceGenerator
                asyncio.create_task(_send_voice_async(platform_user_id=normalized_message.platform_user_id, text=response_text, voice_generator=VoiceGenerator()))
    await history_manager.save_message(conversation_id=conversation["id"], student_id=student["id"], direction=MessageDirection.OUTBOUND.value, content=response_text, message_type=MessageType.TEACHING.value, intent=intent, metadata={"model_used": model_used})
    await event_logger.log_message_exchange(student_id=student["id"], session_id=conversation["id"], intent=intent, student_message=normalized_message.content, waxprep_response=response_text)

async def _send_voice_async(platform_user_id, text, voice_generator):
    try:
        from waxprep.app.gateways.whatsapp.voice_sender import WhatsAppVoiceSender
        audio_bytes = await voice_generator.generate_voice_response(text, max_length=400)
        if audio_bytes:
            await WhatsAppVoiceSender().send_voice_message(platform_user_id, audio_bytes)
    except Exception as e:
        logger.warning(f"Voice send failed: {e}")

async def _check_achievements_async(student_id, event_type, event_data, student_name, platform, platform_user_id):
    try:
        new_achievements = await achievement_engine.check_and_award_achievements(student_id=student_id, event_type=event_type, event_data=event_data)
        for achievement in new_achievements:
            announcement = await achievement_engine.generate_achievement_announcement(achievement=achievement, student_name=student_name, context=event_data)
            await _send_response(platform, platform_user_id, announcement)
    except Exception as e:
        logger.warning(f"Achievement check failed: {e}")

async def _is_new_session(student_id, platform):
    try:
        db = get_db_client()
        timeout = datetime.utcnow() - timedelta(minutes=30)
        response = db.table("conversations").select("id").eq("student_id", student_id).eq("is_active", True).eq("platform", platform).gte("last_message_at", timeout.isoformat()).execute()
        return not bool(response.data)
    except Exception:
        return False

async def _get_active_misconceptions(student_id):
    try:
        db = get_db_client()
        response = db.table("misconceptions").select("description, status, concept_id, subject").eq("student_id", student_id).in_("status", ["active", "resolving"]).limit(5).execute()
        return response.data or []
    except Exception:
        return []

async def _days_since_last_session(student_id):
    try:
        db = get_db_client()
        response = db.table("conversations").select("ended_at").eq("student_id", student_id).eq("is_active", False).order("ended_at", desc=True).limit(1).execute()
        if response.data and response.data[0].get("ended_at"):
            ended = datetime.fromisoformat(response.data[0]["ended_at"].replace("Z", "+00:00"))
            return max(0, (datetime.utcnow().replace(tzinfo=ended.tzinfo) - ended).days)
        return 0
    except Exception:
        return 0

async def _detect_and_store_emotional_context(student_id, session_id, intent, message):
    try:
        if intent not in ["emotional_expression", "EMOTIONAL_EXPRESSION"]: return
        message_lower = message.lower()
        emotional_keywords = {"frustrated": ["frustrated", "confused", "hard", "difficult", "not getting"], "discouraged": ["give up", "can't do", "too hard", "failing", "useless"], "anxious": ["exam", "nervous", "scared", "worried", "afraid", "stress"], "motivated": ["want to learn", "ready", "let's go", "excited", "let's start"]}
        detected = "emotional_expression"
        for state, keywords in emotional_keywords.items():
            if any(kw in message_lower for kw in keywords): detected = state; break
        await event_logger.log_emotional_moment(student_id=student_id, session_id=session_id, emotional_state=detected, trigger=message[:200])
        if detected in ["discouraged", "anxious"]:
            await artifact_writer.write_emotional_note(student_id=student_id, note=f"Student expressed {detected}: {message[:150]}")
    except Exception as e:
        logger.warning(f"Emotional detection failed: {e}")

async def _mark_as_read(normalized_message):
    try:
        if normalized_message.platform == Platform.WHATSAPP:
            from waxprep.app.gateways.whatsapp.sender import WhatsAppSender
            await WhatsAppSender().mark_as_read(normalized_message.platform_message_id)
    except Exception: pass

async def _send_response(platform, platform_user_id, response_text):
    try:
        if platform == Platform.WHATSAPP:
            from waxprep.app.gateways.whatsapp.sender import WhatsAppSender
            await WhatsAppSender().send_text(platform_user_id, response_text)
        elif platform == Platform.TELEGRAM:
            from waxprep.app.gateways.telegram.sender import TelegramSender
            await TelegramSender().send_text(platform_user_id, response_text)
    except Exception as e:
        logger.error(f"Send failed: {e}")

async def _send_error_response(normalized_message):
    try:
        await _send_response(normalized_message.platform, normalized_message.platform_user_id, "I'm having a quick technical moment — try again in a bit.")
    except Exception: pass

async def _update_student_from_interaction(student_id, student, conversation_id, intent, message_content):
    try:
        db = get_db_client()
        profile_check = db.table("student_profiles").select("student_name, current_subject, language_register").eq("student_id", student_id).execute()
        has_name = bool(profile_check.data and profile_check.data[0].get("student_name"))
        has_subject = bool(profile_check.data and profile_check.data[0].get("current_subject"))
        if not student.get("onboarding_complete"):
            current_exchanges = student.get("onboarding_exchanges", 0) + 1
            updates = {"onboarding_exchanges": current_exchanges}
            if (has_name or has_subject or current_exchanges >= 8) and current_exchanges >= 5:
                updates["onboarding_complete"] = True
                await history_manager.update_conversation_state(conversation_id, "teaching")
            db.table("students").update(updates).eq("id", student_id).execute()
        db.table("students").update({"last_active_at": datetime.utcnow().isoformat(), "total_messages_received": (student.get("total_messages_received") or 0) + 1}).eq("id", student_id).execute()
    except Exception as e:
        logger.warning(f"Student update failed: {e}")
