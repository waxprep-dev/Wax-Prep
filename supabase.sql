-- ============================================
-- DAVID OS — Complete Supabase Schema
-- 15 tables with RLS, indexes, triggers
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. CONTACTS (Enhanced with trust scoring)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200),
    phone_number VARCHAR(30) UNIQUE NOT NULL,
    normalized_phone VARCHAR(30) UNIQUE,
    relationship_type VARCHAR(20) DEFAULT 'stranger' 
        CHECK (relationship_type IN ('family', 'close_friend', 'business', 'acquaintance', 'stranger')),
    relationship_score FLOAT DEFAULT 0.0,
    notes TEXT,
    always_alert BOOLEAN DEFAULT FALSE,
    ghost_mode BOOLEAN DEFAULT FALSE,
    ai_enabled BOOLEAN DEFAULT TRUE,
    trust_level INTEGER DEFAULT 50 CHECK (trust_level BETWEEN 0 AND 100),
    language_preference VARCHAR(10) DEFAULT 'en',
    tags TEXT[] DEFAULT '{}',
    last_interaction TIMESTAMPTZ,
    message_count INTEGER DEFAULT 0,
    incoming_count INTEGER DEFAULT 0,
    outgoing_count INTEGER DEFAULT 0,
    avg_confidence FLOAT DEFAULT 0,
    voice_notes_count INTEGER DEFAULT 0,
    blocked BOOLEAN DEFAULT FALSE,
    spam_score FLOAT DEFAULT 0,
    source VARCHAR(50) DEFAULT 'whatsapp',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_contacts_phone ON davidos_contacts(phone_number);
CREATE INDEX idx_contacts_relationship ON davidos_contacts(relationship_type);
CREATE INDEX idx_contacts_alert ON davidos_contacts(always_alert);
CREATE INDEX idx_contacts_trust ON davidos_contacts(trust_level);
CREATE INDEX idx_contacts_interaction ON davidos_contacts(last_interaction DESC);
CREATE INDEX idx_contacts_tags ON davidos_contacts USING GIN(tags);

-- ============================================
-- 2. MESSAGES (Enhanced with sentiment & analysis)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID REFERENCES davidos_contacts(id) ON DELETE CASCADE,
    phone_number VARCHAR(30) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text' CHECK (content_type IN ('text', 'image', 'voice', 'video', 'document', 'location', 'sticker')),
    media_url TEXT,
    ai_generated BOOLEAN DEFAULT FALSE,
    confidence_score FLOAT,
    status VARCHAR(20) DEFAULT 'sent' CHECK (status IN ('pending', 'sent', 'delivered', 'read', 'failed', 'queued')),
    
    -- Sentiment analysis
    sentiment VARCHAR(10) CHECK (sentiment IN ('positive', 'negative', 'neutral', 'mixed')),
    sentiment_score FLOAT,
    
    -- Emotional detection
    emotion VARCHAR(20) CHECK (emotion IN ('happy', 'sad', 'angry', 'excited', 'anxious', 'neutral', 'urgent', 'grateful')),
    
    -- Context tracking
    context_summary TEXT,
    topics TEXT[] DEFAULT '{}',
    entities TEXT[] DEFAULT '{}',
    intent VARCHAR(50),
    
    -- Engagement metrics
    response_time_ms INTEGER,
    char_count INTEGER,
    word_count INTEGER,
    language_detected VARCHAR(10),
    
    -- Threading
    thread_id UUID,
    reply_to UUID REFERENCES davidos_messages(id),
    
    -- Metadata
    raw_payload JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_contact ON davidos_messages(contact_id);
CREATE INDEX idx_messages_phone ON davidos_messages(phone_number);
CREATE INDEX idx_messages_created ON davidos_messages(created_at DESC);
CREATE INDEX idx_messages_direction ON davidos_messages(direction);
CREATE INDEX idx_messages_ai ON davidos_messages(ai_generated);
CREATE INDEX idx_messages_status ON davidos_messages(status);
CREATE INDEX idx_messages_sentiment ON davidos_messages(sentiment);
CREATE INDEX idx_messages_emotion ON davidos_messages(emotion);
CREATE INDEX idx_messages_type ON davidos_messages(content_type);
CREATE INDEX idx_messages_topics ON davidos_messages USING GIN(topics);
CREATE INDEX idx_messages_metadata ON davidos_messages USING GIN(metadata);

-- ============================================
-- 3. CONVERSATIONS (Thread management)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID REFERENCES davidos_contacts(id) ON DELETE CASCADE,
    title VARCHAR(500),
    summary TEXT,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'archived', 'escalated')),
    ai_handled BOOLEAN DEFAULT TRUE,
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    last_message_preview TEXT,
    context_window JSONB DEFAULT '[]',
    summary_text TEXT,
    summary_updated_at TIMESTAMPTZ,
    engagement_score FLOAT DEFAULT 0,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_conversations_contact ON davidos_conversations(contact_id);
CREATE INDEX idx_conversations_status ON davidos_conversations(status);
CREATE INDEX idx_conversations_active ON davidos_conversations(last_message_at DESC);

-- ============================================
-- 4. ESCALATIONS (Enhanced with severity routing)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_escalations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID REFERENCES davidos_contacts(id) ON DELETE CASCADE,
    message_id UUID REFERENCES davidos_messages(id),
    conversation_id UUID REFERENCES davidos_conversations(id),
    reason VARCHAR(100) NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    category VARCHAR(50) CHECK (category IN ('emergency', 'money', 'emotional_crisis', 'privacy', 'repeated_contact', 'manual_alert', 'ai_confused', 'system_error')),
    details JSONB DEFAULT '{}',
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(50),
    resolution_notes TEXT,
    auto_escalated BOOLEAN DEFAULT TRUE,
    notification_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_escalations_contact ON davidos_escalations(contact_id);
CREATE INDEX idx_escalations_severity ON davidos_escalations(severity);
CREATE INDEX idx_escalations_resolved ON davidos_escalations(resolved);
CREATE INDEX idx_escalations_created ON davidos_escalations(created_at DESC);

-- ============================================
-- 5. PERSONALITY LAYERS (Enhanced with NLP patterns)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_personality (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    layer VARCHAR(50) NOT NULL,
    version INTEGER DEFAULT 1,
    prompt_text TEXT NOT NULL,
    system_prompt TEXT,
    few_shot_examples JSONB DEFAULT '[]',
    tone_adjectives TEXT[] DEFAULT '{}',
    vocabulary_rules JSONB DEFAULT '{}',
    response_patterns JSONB DEFAULT '{}',
    emoji_frequency FLOAT DEFAULT 0.3,
    avg_response_length INTEGER DEFAULT 50,
    code_switching_rules JSONB DEFAULT '{}',
    formality_score INTEGER DEFAULT 50 CHECK (formality_score BETWEEN 0 AND 100),
    humor_level INTEGER DEFAULT 50 CHECK (humor_level BETWEEN 0 AND 100),
    active BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(50) DEFAULT 'system',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(layer, version)
);

CREATE INDEX idx_personality_layer ON davidos_personality(layer);
CREATE INDEX idx_personality_active ON davidos_personality(active);

-- ============================================
-- 6. VOICE NOTES (Enhanced with transcription & embeddings)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_voice_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID REFERENCES davidos_contacts(id),
    file_path TEXT,
    file_url TEXT,
    duration INTEGER,
    file_size INTEGER,
    mime_type VARCHAR(50),
    transcribed_text TEXT,
    transcription_confidence FLOAT,
    embedding VECTOR(1536),
    language_detected VARCHAR(10),
    speaker_tags JSONB DEFAULT '[]',
    processed BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_voice_contact ON davidos_voice_notes(contact_id);
CREATE INDEX idx_voice_processed ON davidos_voice_notes(processed);

-- ============================================
-- 7. SETTINGS (Enhanced with feature flags)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    data_type VARCHAR(20) DEFAULT 'string' CHECK (data_type IN ('string', 'number', 'boolean', 'json', 'array')),
    category VARCHAR(50) DEFAULT 'general',
    description TEXT,
    editable BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_settings_key ON davidos_settings(key);
CREATE INDEX idx_settings_category ON davidos_settings(category);

-- ============================================
-- 8. LEARNING FEEDBACK (AI improvement loop)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID REFERENCES davidos_messages(id),
    contact_id UUID REFERENCES davidos_contacts(id),
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('correction', 'rating', 'override', 'suggestion', 'block')),
    original_response TEXT,
    corrected_response TEXT,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    notes TEXT,
    applied_to_model BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feedback_contact ON davidos_feedback(contact_id);
CREATE INDEX idx_feedback_type ON davidos_feedback(feedback_type);
CREATE INDEX idx_feedback_applied ON davidos_feedback(applied_to_model);

-- ============================================
-- 9. ANALYTICS (Time-series metrics)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    dimension VARCHAR(50),
    dimension_value VARCHAR(200),
    period VARCHAR(20) CHECK (period IN ('hourly', 'daily', 'weekly', 'monthly')),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_analytics_name ON davidos_analytics(metric_name);
CREATE INDEX idx_analytics_period ON davidos_analytics(recorded_at DESC);
CREATE INDEX idx_analytics_dimension ON davidos_analytics(dimension, dimension_value);

-- ============================================
-- 10. COST TRACKING (API usage & costs)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_costs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    service VARCHAR(50) NOT NULL CHECK (service IN ('groq', 'openai', 'supabase', 'render', 'other')),
    operation VARCHAR(100) NOT NULL,
    model VARCHAR(50),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost_usd DECIMAL(10,6) DEFAULT 0,
    request_duration_ms INTEGER,
    contact_id UUID REFERENCES davidos_contacts(id),
    message_id UUID REFERENCES davidos_messages(id),
    success BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_costs_service ON davidos_costs(service);
CREATE INDEX idx_costs_created ON davidos_costs(created_at DESC);
CREATE INDEX idx_costs_contact ON davidos_costs(contact_id);

-- ============================================
-- 11. RESPONSE QUEUE (Pending approval messages)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_response_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID REFERENCES davidos_contacts(id),
    message_id UUID REFERENCES davidos_messages(id),
    incoming_message TEXT NOT NULL,
    suggested_response TEXT NOT NULL,
    ai_confidence FLOAT,
    context_summary TEXT,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'edited', 'expired')),
    edited_response TEXT,
    reviewed_by VARCHAR(50),
    reviewed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '24 hours',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_queue_status ON davidos_response_queue(status);
CREATE INDEX idx_queue_expires ON davidos_response_queue(expires_at);

-- ============================================
-- 12. SCHEDULED MESSAGES (Future sends)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_scheduled_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contact_id UUID REFERENCES davidos_contacts(id),
    phone_number VARCHAR(30) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text',
    scheduled_at TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'sent', 'cancelled', 'failed', 'sending')),
    recurrence VARCHAR(20) CHECK (recurrence IN ('none', 'daily', 'weekly', 'monthly')),
    created_by VARCHAR(50) DEFAULT 'system',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scheduled_status ON davidos_scheduled_messages(status);
CREATE INDEX idx_scheduled_time ON davidos_scheduled_messages(scheduled_at);

-- ============================================
-- 13. TEMPLATES (Quick response templates)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    shortcut VARCHAR(50) UNIQUE,
    content TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    variables JSONB DEFAULT '[]',
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_templates_category ON davidos_templates(category);
CREATE INDEX idx_templates_active ON davidos_templates(active);
CREATE INDEX idx_templates_shortcut ON davidos_templates(shortcut);

-- ============================================
-- 14. AUDIT LOG (Complete activity tracking)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    actor VARCHAR(100),
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_action ON davidos_audit_log(action);
CREATE INDEX idx_audit_entity ON davidos_audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_created ON davidos_audit_log(created_at DESC);

-- ============================================
-- 15. KNOWLEDGE BASE (David's info & facts)
-- ============================================
CREATE TABLE IF NOT EXISTS davidos_knowledge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category VARCHAR(100) NOT NULL,
    key VARCHAR(500) NOT NULL,
    value TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source VARCHAR(100),
    embedding VECTOR(1536),
    times_accessed INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_knowledge_category ON davidos_knowledge(category);
CREATE INDEX idx_knowledge_key ON davidos_knowledge(key);
CREATE INDEX idx_knowledge_active ON davidos_knowledge(active);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER trigger_contacts_updated_at BEFORE UPDATE ON davidos_contacts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_personality_updated_at BEFORE UPDATE ON davidos_personality
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_conversations_updated_at BEFORE UPDATE ON davidos_conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_settings_updated_at BEFORE UPDATE ON davidos_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trigger_knowledge_updated_at BEFORE UPDATE ON davidos_knowledge
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Update contact stats on new message
CREATE OR REPLACE FUNCTION update_contact_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE davidos_contacts SET
        message_count = message_count + 1,
        incoming_count = CASE WHEN NEW.direction = 'inbound' THEN incoming_count + 1 ELSE incoming_count END,
        outgoing_count = CASE WHEN NEW.direction = 'outbound' THEN outgoing_count + 1 ELSE outgoing_count END,
        last_interaction = NEW.created_at,
        updated_at = NOW()
    WHERE id = NEW.contact_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_message_stats AFTER INSERT ON davidos_messages
    FOR EACH ROW EXECUTE FUNCTION update_contact_stats();

-- Update conversation on new message
CREATE OR REPLACE FUNCTION update_conversation_activity()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE davidos_conversations SET
        message_count = message_count + 1,
        last_message_at = NEW.created_at,
        last_message_preview = LEFT(NEW.content, 100),
        updated_at = NOW()
    WHERE contact_id = NEW.contact_id AND status = 'active';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_conversation_activity AFTER INSERT ON davidos_messages
    FOR EACH ROW EXECUTE FUNCTION update_conversation_activity();

-- ============================================
-- SEED DATA
-- ============================================

-- Default personality layers
INSERT INTO davidos_personality (layer, prompt_text, system_prompt, few_shot_examples, tone_adjectives, emoji_frequency, formality_score, humor_level) VALUES
('family', 
'You are David talking to family. Be warm, respectful, caring. Use "sir", "ma", "mama". Quick responses. Never joke about serious family matters. Show genuine concern. Use Nigerian terms of endearment. Always ask about wellbeing. Be protective and supportive.',
'Family mode: Maximum warmth and respect. Nigerian family values. Respond like a loving son/brother/nephew.',
'[{"input": "How are you doing?", "output": "I dey fine ma! 🙏 How body? Hope you rested well?"}, {"input": "Your uncle is in hospital", "output": "Ah! Which hospital ma? I go come now now. Make I bring anything?"}]'::jsonb,
'{"warm", "respectful", "caring", "protective", "nurturing"}'::text[],
0.4, 70, 30
)
ON CONFLICT (layer, version) DO NOTHING;

INSERT INTO davidos_personality (layer, prompt_text, system_prompt, few_shot_examples, tone_adjectives, emoji_frequency, formality_score, humor_level) VALUES
('close_friend', 
'You are David with close friends. Playful, free with pidgin, jokes, teases. Send rapid short messages. Use slang freely. Roast each other lovingly. No filters but stay respectful. Match their energy. Use street vibes. Be loyal and real.',
'Close friend mode: Maximum vibes. Pure Lagos energy. No formality. Real gees mode activated.',
'[{"input": "Guy you no show yesterday", "output": "😂 Omo I dey around nau! You just dey find excuse to chop my money sha"}, {"input": "I got the job!", "output": "Ehen! I talk am! 💯💯 My guy! We must turn up this weekend! 🚀🚀🚀"}]'::jsonb,
'{"playful", "energetic", "loyal", "teasing", "unfiltered"}'::text[],
0.6, 20, 85
)
ON CONFLICT (layer, version) DO NOTHING;

INSERT INTO davidos_personality (layer, prompt_text, system_prompt, few_shot_examples, tone_adjectives, emoji_frequency, formality_score, humor_level) VALUES
('business', 
'You are David in business mode. Sharp, direct, professional but warm. Ask clarifying questions. Negotiate smartly. Never agree to first price. Always say "Let me review and get back to you." Use full English. Be confident and knowledgeable. Protect David''s interests.',
'Business mode: Professional excellence. Sharp negotiation. Strategic thinking. Protect value.',
'[{"input": "We can do it for 500k", "output": "I appreciate the offer. Let me review the scope properly and I\'ll get back to you. What\'s the timeline looking like?"}, {"input": "Are you available for a meeting?", "output": "Yes, I can make time. What\'s the agenda? And would a call work or do you prefer in-person?"}]'::jsonb,
'{"sharp", "professional", "strategic", "confident", "diplomatic"}'::text[],
0.2, 85, 20
)
ON CONFLICT (layer, version) DO NOTHING;

INSERT INTO davidos_personality (layer, prompt_text, system_prompt, few_shot_examples, tone_adjectives, emoji_frequency, formality_score, humor_level) VALUES
('acquaintance', 
'You are David with acquaintances. Polite, brief, helpful but not overly familiar. Professional warmth. Clear communication. No excessive slang. Respect boundaries. Be approachable but maintain distance.',
'Acquaintance mode: Polite professionalism. Friendly distance. Clear boundaries.',
'[{"input": "Nice to meet you", "output": "Likewise! Pleasure connecting. How can I help?"}]'::jsonb,
'{"polite", "reserved", "helpful", "clear", "approachable"}'::text[],
0.2, 60, 40
)
ON CONFLICT (layer, version) DO NOTHING;

INSERT INTO davidos_personality (layer, prompt_text, system_prompt, few_shot_examples, tone_adjectives, emoji_frequency, formality_score, humor_level) VALUES
('stranger', 
'You are David with strangers. Brief, polite. Ask who they are and what they need. Cautious but not rude. Professional boundary. If they seem genuine, gradually warm up.',
'Stranger mode: Cautious politeness. Verify before trusting. Professional first impression.',
'[{"input": "Hello", "output": "Hi there! May I know who this is?"}, {"input": "I got your number from John", "output": "Oh nice. How can I help you today?"}]'::jsonb,
'{"cautious", "polite", "brief", "professional", "guarded"}'::text[],
0.1, 75, 10
)
ON CONFLICT (layer, version) DO NOTHING;

-- Default settings
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('ai_enabled', 'true', 'boolean', 'system', 'Master AI toggle') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('confidence_threshold', '0.7', 'number', 'ai', 'Minimum confidence to auto-send') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('quiet_hours_start', '00:00', 'string', 'time', 'Start of quiet hours') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('quiet_hours_end', '06:00', 'string', 'time', 'End of quiet hours') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('typing_delay_min', '2000', 'number', 'behavior', 'Minimum typing delay in ms') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('typing_delay_max', '8000', 'number', 'behavior', 'Maximum typing delay in ms') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('auto_archive_days', '90', 'number', 'maintenance', 'Auto-archive conversations after days') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('max_message_length', '500', 'number', 'behavior', 'Maximum characters per message') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('negotiation_budget_threshold', '50000', 'number', 'business', 'Naira threshold for deal alerts') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('response_style', 'natural', 'string', 'behavior', 'Overall response style') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('self_reveal_default', 'false', 'boolean', 'privacy', 'Default AI revelation setting') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('emergency_alert', 'true', 'boolean', 'safety', 'Alert on emergency keywords') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('cost_limit_daily_usd', '10.00', 'number', 'cost', 'Daily API cost limit') ON CONFLICT (key) DO NOTHING;
INSERT INTO davidos_settings (key, value, data_type, category, description) VALUES
('conversation_summary_threshold', '50', 'number', 'ai', 'Messages before summarizing context') ON CONFLICT (key) DO NOTHING;

-- Sample templates
INSERT INTO davidos_templates (name, shortcut, content, category) VALUES
('Busy Reply', '/busy', 'Currently tied up bro. Let me get back to you shortly. 🙏', 'quick') ON CONFLICT DO NOTHING;
INSERT INTO davidos_templates (name, shortcut, content, category) VALUES
('Meeting Request', '/meet', 'I can make time. What works for you? I\'m generally free [TIME_OPTIONS].', 'business') ON CONFLICT DO NOTHING;
INSERT INTO davidos_templates (name, shortcut, content, category) VALUES
('Budget Request', '/budget', 'Thanks for reaching out. What\'s your budget for this? And what\'s the timeline?', 'business') ON CONFLICT DO NOTHING;
INSERT INTO davidos_templates (name, shortcut, content, category) VALUES
('Check Back', '/check', 'Let me check this properly and I\'ll get back to you. Give me some time.', 'general') ON CONFLICT DO NOTHING;

-- Enable RLS (basic security)
ALTER TABLE davidos_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE davidos_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE davidos_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE davidos_escalations ENABLE ROW LEVEL SECURITY;
ALTER TABLE davidos_settings ENABLE ROW LEVEL SECURITY;

-- Create access policies (service role bypasses these)
CREATE POLICY "Allow all" ON davidos_contacts FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON davidos_messages FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON davidos_conversations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON davidos_escalations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all" ON davidos_settings FOR ALL USING (true) WITH CHECK (true);

-- Add pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================
-- COMPLETE — DAVID OS Database Ready
-- ============================================
