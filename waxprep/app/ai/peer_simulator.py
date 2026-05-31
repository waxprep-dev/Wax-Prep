import json
import random
from typing import Dict, Any, Optional, List
from loguru import logger
from groq import Groq
from waxprep.app.core.config import settings
from waxprep.app.database.client import get_db_client

PEER_PROFILES = [
    {
        "name": "Tunde",
        "level": "SS2",
        "personality": "confident but makes mistakes, quick to guess, needs to be corrected sometimes",
        "weakness": "tends to rush and skip steps in calculations",
        "strength": "good conceptual understanding, explains things clearly to others",
        "catchphrase": "Wait, so if I do it this way..."
    },
    {
        "name": "Amara",
        "level": "SS2",
        "personality": "methodical and careful, asks lots of clarifying questions",
        "weakness": "second-guesses herself even when she is right",
        "strength": "remembers formulas well, great at showing working",
        "catchphrase": "Hold on, let me check this again..."
    },
    {
        "name": "Chidi",
        "level": "SS3",
        "personality": "WAEC-focused, practical, wants to know exactly what the examiner wants",
        "weakness": "relies too much on memorizing without understanding",
        "strength": "excellent at past question recognition and exam technique",
        "catchphrase": "But how would you write this in WAEC format?"
    },
    {
        "name": "Fatima",
        "level": "SS1",
        "personality": "curious and creative, often finds unexpected connections between topics",
        "weakness": "sometimes overthinks simple questions",
        "strength": "great at generating examples and seeing patterns",
        "catchphrase": "Oh! This is like what we learned in..."
    },
]

PEER_STUDY_SETUP_PROMPT = """You are WaxPrep running a peer study simulation.
A Nigerian student wants to study with a simulated peer to practice explaining concepts and working through problems together.

The simulated peer is: {peer_name}
Peer personality: {peer_personality}
Peer weakness: {peer_weakness}
Peer strength: {peer_strength}

Topic being studied: {topic}
Subject: {subject}
Class level: {class_level}

Rules for the peer simulation:
1. Play as {peer_name} — a student studying the same material
2. The peer should ask the main student questions and attempt answers themselves sometimes
3. The peer should sometimes get things slightly wrong so the main student can correct them
4. The peer should occasionally make exactly the type of error that is documented as common for this topic
5. The peer should celebrate when both students understand something
6. This is educational peer study, not entertainment — the goal is learning
7. Keep {peer_name}'s contributions short and natural, like a real student would text
8. Sometimes use Nigerian student expressions naturally

The main student's message: {student_message}

Respond as {peer_name} in this study session. Be natural, educational, occasionally wrong in pedagogically useful ways, and genuinely engaged."""

class PeerSimulator:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.groq_api_key)
        self.db = get_db_client()
        self._active_sessions: Dict[str, Dict] = {}
    
    async def start_peer_session(
        self, student_id: str, topic: str, subject: str,
        class_level: str, student_name: str = "there",
    ) -> str:
        peer = random.choice(PEER_PROFILES)
        self._active_sessions[student_id] = {
            "peer": peer, "topic": topic, "subject": subject,
            "class_level": class_level, "exchanges": 0, "student_name": student_name,
        }
        return (
            f"Okay so I'm setting up a peer study session for you on {topic}. "
            f"You're studying with {peer['name']} — same level as you, working through the same material. "
            f"This is a simulation, not a real person, but it works the same way: "
            f"explain things to each other, quiz each other, and correct each other when something's off. "
            f"\n\n{peer['name']}: Hey! So we're doing {topic}? I've been struggling with this. "
            f"Where do you want to start?"
        )
    
    async def process_peer_exchange(self, student_id: str, student_message: str) -> Optional[str]:
        session = self._active_sessions.get(student_id)
        if not session:
            return None
        peer = session["peer"]
        session["exchanges"] += 1
        try:
            prompt = PEER_STUDY_SETUP_PROMPT.format(
                peer_name=peer["name"], peer_personality=peer["personality"],
                peer_weakness=peer["weakness"], peer_strength=peer["strength"],
                topic=session["topic"], subject=session["subject"],
                class_level=session["class_level"], student_message=student_message,
            )
            response = self.groq_client.chat.completions.create(
                model=settings.groq_fast_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200, temperature=0.8,
            )
            peer_response = response.choices[0].message.content.strip()
            if not peer_response.startswith(peer["name"]):
                peer_response = f"{peer['name']}: {peer_response}"
            if session["exchanges"] % 5 == 0:
                peer_response += (
                    f"\n\n[WaxPrep: Good session so far. "
                    f"You've covered {session['exchanges']} exchanges on {session['topic']}. "
                    f"I'm tracking what you explain — how you explain it to {peer['name']} "
                    f"tells me a lot about what you actually understand. Keep going.]"
                )
            return peer_response
        except Exception as e:
            logger.error(f"Peer simulation failed: {e}")
            return f"{peer['name']}: Hmm, I'm thinking about that. What do you think?"
    
    def has_active_session(self, student_id: str) -> bool:
        return student_id in self._active_sessions
    
    async def end_peer_session(self, student_id: str) -> Optional[str]:
        session = self._active_sessions.pop(student_id, None)
        if not session:
            return None
        return (
            f"Peer study session with {session['peer']['name']} complete. "
            f"You covered {session['exchanges']} exchanges on {session['topic']}. "
            f"The way you explained things to {session['peer']['name']} showed me a lot about "
            f"where your understanding is solid and where there are still gaps. "
            f"Want me to run a quick assessment to confirm what stuck?"
        )
    
    def is_peer_session_trigger(self, message: str) -> bool:
        triggers = [
            "study with someone", "peer study", "study partner",
            "study together", "let me practice explaining",
            "practice with a friend", "teach someone",
            "explain to someone", "quiz me like a friend",
        ]
        return any(t in message.lower() for t in triggers)
    
    def is_peer_session_end(self, message: str) -> bool:
        ends = [
            "end peer", "stop peer", "end session", "leave peer",
            "exit peer", "done with peer", "stop simulation",
        ]
        return any(e in message.lower() for e in ends)
