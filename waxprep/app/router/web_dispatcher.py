import asyncio
from typing import Optional
from datetime import datetime
from loguru import logger
from waxprep.app.gateways.normalizer import NormalizedMessage
from waxprep.app.identity.manager import IdentityManager
from waxprep.app.conversation.history_manager import ConversationHistoryManager
from waxprep.app.ai.engine import WaxPrepAIEngine
from waxprep.app.ai.prompts import build_teaching_prompt, build_knowledge_map_summary
from waxprep.app.cache.student_cache import StudentCache
from waxprep.app.memory.artifact_writer import MemoryArtifactWriter
from waxprep.app.memory.session_summary import SessionSummaryGenerator
from waxprep.app.ai.profile_extractor import ProfileIntelligenceExtractor
from waxprep.app.ai.subject_detector import detect_subject_and_topic
from waxprep.app.ai.subject_router import get_teaching_intelligence
from waxprep.app.ai.frustration_detector import FrustrationDetector
from waxprep.app.core.time_awareness import get_time_context_string
from waxprep.app.database.client import get_db_client

identity_manager = IdentityManager()
history_manager = ConversationHistoryManager()
ai_engine = WaxPrepAIEngine()
student_cache = StudentCache()
artifact_writer = MemoryArtifactWriter()
profile_extractor = ProfileIntelligenceExtractor()
frustration_detector = FrustrationDetector()

async def dispatch_web_message(normalized_message: NormalizedMessage, student_id: str) -> str:
    try:
        student = get_db_client().table("students").select("*").eq("id", student_id).execute()
        if not student.data: return "Session error — please log in again."
        student_data = student.data[0]
        
        conversation = await history_manager.get_or_create_active_conversation(student_id=student_id, platform="whatsapp")
        
        from waxprep.app.core.constants import MessageDirection, MessageType
        await history_manager.save_message(conversation_id=conversation["id"], student_id=student_id, direction=MessageDirection.INBOUND.value, content=normalized_message.content, message_type="text")
        
        conversation_history = await history_manager.get_conversation_history_for_ai(conversation_id=conversation["id"], limit=15)
        
        intent = await ai_engine.classify_intent(message=normalized_message.content, recent_context=" | ".join([m["content"][:50] for m in conversation_history[-3:] if m["role"] == "user"]))
        
        student_profile_data = await student_cache.get_student_profile(student_id)
        merged_student_data = {**student_data}
        if student_profile_data: merged_student_data["profile"] = student_profile_data
        
        detected_subject, detected_topic = detect_subject_and_topic(normalized_message.content)
        current_subject = detected_subject or (student_profile_data.get("current_subject") if student_profile_data else None)
        current_topic = detected_topic or (student_profile_data.get("current_topic") if student_profile_data else None)
        
        memory_context = await artifact_writer.build_memory_context_string(student_id)
        knowledge_map_items = await student_cache.get_knowledge_map(student_id)
        knowledge_map_summary_text = build_knowledge_map_summary(knowledge_map_items)
        
        active_misconceptions = []
        try:
            misc_response = get_db_client().table("misconceptions").select("description, status").eq("student_id", student_id).in_("status", ["active"]).limit(3).execute()
            active_misconceptions = misc_response.data or []
        except Exception: pass
        
        subject_intelligence = ""
        if current_subject or current_topic:
            subject_intelligence = await get_teaching_intelligence(subject=current_subject or "", topic=current_topic or "", class_level=student_data.get("inferred_class_level", "SS1"), misconceptions=[m.get("description", "") for m in active_misconceptions])
        
        frustration_analysis = frustration_detector.analyze_message(student_id=student_id, message=normalized_message.content, intent=intent)
        frustration_instruction = frustration_detector.get_strategy_instruction(frustration_analysis=frustration_analysis, current_topic=current_topic or "current topic")
        
        time_context = get_time_context_string()
        
        system_prompt, messages = build_teaching_prompt(
            student_profile=merged_student_data, conversation_history=conversation_history[:-1],
            current_message=normalized_message.content, session_state=conversation.get("session_state", "teaching"),
            active_misconceptions=active_misconceptions, current_topic=current_topic, current_subject=current_subject,
            memory_context=memory_context if memory_context else None,
            knowledge_map_summary=knowledge_map_summary_text if knowledge_map_summary_text else None,
            subject_intelligence=subject_intelligence if subject_intelligence else None,
            frustration_instruction=frustration_instruction if frustration_instruction else None,
            current_datetime=time_context,
        )
        
        ai_result = await ai_engine.generate_teaching_response_from_prompt(system_prompt=system_prompt, messages=messages)
        response_text = ai_result["response"]
        
        await history_manager.save_message(conversation_id=conversation["id"], student_id=student_id, direction=MessageDirection.OUTBOUND.value, content=response_text, message_type=MessageType.TEACHING.value, intent=intent)
        
        if len(conversation_history) % 5 == 0:
            asyncio.create_task(profile_extractor.extract_and_update(student_id=student_id, conversation_history=conversation_history))
        
        return response_text
    except Exception as e:
        logger.error(f"Web dispatch error: {e}", exc_info=True)
        return "I'm having a quick technical moment — please try again."
