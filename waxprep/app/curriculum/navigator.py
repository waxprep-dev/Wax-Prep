"""Curriculum navigator - loads and navigates Nigerian curriculum JSON files."""
import json
import os
from typing import Dict, Any, Optional, List

class CurriculumNavigator:
    def __init__(self):
        self._cache = {}
        self._base_path = os.path.dirname(os.path.abspath(__file__))
    
    def load_curriculum(self, subject: str, class_level: str) -> Optional[Dict[str, Any]]:
        """Load a curriculum file. Returns None if not found."""
        if not subject or not class_level:
            return None
        cache_key = f"{subject}_{class_level}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Determine the file path
        class_level = class_level.upper().replace(" ", "")
        subject = subject.lower().replace(" ", "_")
        
        # Try SSS curriculum first, then JSS
        possible_paths = [
            f"sss_curriculum/{class_level}_{subject}.json",
            f"jss_curriculum/{class_level}_{subject}.json",
        ]
        
        for rel_path in possible_paths:
            full_path = os.path.join(self._base_path, rel_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r') as f:
                        data = json.load(f)
                    self._cache[cache_key] = data
                    return data
                except (json.JSONDecodeError, IOError):
                    pass
        return None
    
    def get_next_topic(self, current_topic: str, subject: str, class_level: str) -> Optional[str]:
        """Get the next topic in sequence."""
        curriculum = self.load_curriculum(subject, class_level)
        if not curriculum:
            return None
        topics = curriculum.get("topics", [])
        for i, t in enumerate(topics):
            if t.get("title", "").lower() == current_topic.lower():
                if i + 1 < len(topics):
                    return topics[i + 1]["title"]
        return None
    
    def get_topic_concepts(self, subject: str, topic: str, class_level: str) -> List[str]:
        """Get concepts for a specific topic."""
        curriculum = self.load_curriculum(subject, class_level)
        if not curriculum:
            return []
        for t in curriculum.get("topics", []):
            if t.get("title", "").lower() == topic.lower():
                concepts = []
                for sub in t.get("subtopics", []):
                    concepts.extend(sub.get("concepts", []))
                return concepts
        return []
    
    def get_common_misconceptions(self, subject: str, topic: str, class_level: str) -> List[str]:
        """Get common misconceptions for a topic."""
        curriculum = self.load_curriculum(subject, class_level)
        if not curriculum:
            return []
        for t in curriculum.get("topics", []):
            if t.get("title", "").lower() == topic.lower():
                misconceptions = []
                for sub in t.get("subtopics", []):
                    misconceptions.extend(sub.get("common_misconceptions", []))
                return misconceptions
        return []
    
    def get_waec_priority_topics(self, subject: str, class_level: str) -> List[str]:
        """Get WAEC high-priority topics."""
        curriculum = self.load_curriculum(subject, class_level)
        if not curriculum:
            return []
        return curriculum.get("waec_high_priority_topics", [])
    
    def get_concept_prerequisites(self, concept: str, subject: str, class_level: str) -> List[str]:
        """Get prerequisites for a concept."""
        curriculum = self.load_curriculum(subject, class_level)
        if not curriculum:
            return []
        for t in curriculum.get("topics", []):
            for sub in t.get("subtopics", []):
                for c in sub.get("concepts", []):
                    if isinstance(c, dict) and c.get("name", "").lower() == concept.lower():
                        return c.get("prerequisites", [])
        return []
