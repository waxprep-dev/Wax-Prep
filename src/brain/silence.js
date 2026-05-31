// ============================================
// DAVID OS — Silence Intelligence
// Knowing when NOT to reply is as important as replying
// ============================================

const { logger } = require('../utils/logger');

// Patterns that should trigger silence
const SILENCE_PATTERNS = {
    // Exact match standalone acknowledgments
    standalone: [
        /^ok$/i,
        /^okay$/i,
        /^k$/i,
        /^kk$/i,
        /^seen$/i,
        /^lol$/i,
        /^lmao$/i,
        /^haha$/i,
        /^hahaha$/i,
        /^cool$/i,
        /^nice$/i,
        /^noted$/i,
        /^alright$/i,
        /^aight$/i,
        /^bet$/i,
        /^got it$/i,
        /^sure$/i,
        /^yep$/i,
        /^yeah$/i,
        /^yes$/i,
        /^no$/i,
        /^nope$/i,
        /^thanks$/i,
        /^thank you$/i,
        /^ty$/i,
        /^👍$/,
        /^💯$/,
        /^✅$/,
        /^👌$/,
        /^🙏$/,
        /^❤️$/,
        /^🔥$/,
        /^😂$/,
        /^🤣$/,
        /^😊$/,
        /^👋$/,
        /^🙂$/,
        /^\.$/,
        /^\.+$/,  // Just dots
    ],
    
    // End-of-conversation signals
    closingSignals: [
        /\b(bye|goodbye|see you|talk to you later|ttyl|cya|gn|good night|night night)\b/i,
        /\b(let me go|i have to run|i gotta go|i need to go)\b/i,
        /\b(catch you later|hit you up later|we go talk later)\b/i,
    ],
    
    // Conversation death patterns (consecutive short exchanges)
    acknowledgmentChain: [
        /^(ok|okay|k|seen|cool|alright|bet|yes|yeah|sure)$/i,
    ]
};

// Triggers that OVERRIDE silence (always respond)
const OVERRIDE_TRIGGERS = [
    /\b(urgent|emergency|help|please|asap|quickly)\b/i,
    /\?/, // Questions
    /\b(call me|call you|phone|voice note|vn)\b/i,
    /\b(money|pay|payment|price|cost|urgent)\b/i,
    /^\d+\s+naira/i,
    /^\₦/,
];

class SilenceEngine {
    constructor() {
        this.recentExchanges = new Map(); // contactId -> array of last exchanges
        this.maxTrackedExchanges = 10;
        this.acknowledgmentStreakThreshold = 3;
    }
    
    // ============================================
    // Main Decision: Should we reply?
    // ============================================
    async shouldReply(message, contact, context = []) {
        const content = (message.content || message).trim();
        const contentLower = content.toLowerCase();
        
        // Always reply overrides
        if (this.hasOverride(content)) {
            logger.info('SILENCE_OVERRIDE', { reason: 'override_trigger', contactId: contact.id, content: content.substring(0, 50) });
            return { shouldReply: true, reason: 'override_trigger' };
        }
        
        // Check always_alert contacts
        if (contact.always_alert) {
            return { shouldReply: true, reason: 'always_alert_contact' };
        }
        
        // Check ghost mode
        if (contact.ghost_mode) {
            return { shouldReply: false, reason: 'ghost_mode', action: 'watch_only' };
        }
        
        // Check if AI is globally disabled
        const { Settings } = require('../utils/supabase');
        const aiEnabled = await Settings.get('ai_enabled', true);
        if (!aiEnabled) {
            return { shouldReply: false, reason: 'ai_disabled' };
        }
        
        // Check standalone acknowledgment
        if (this.isStandaloneAcknowledgment(content)) {
            logger.info('SILENCE_DETECTED', { reason: 'standalone_ack', content: content.substring(0, 30) });
            return { shouldReply: false, reason: 'standalone_acknowledgment', action: 'stay_silent' };
        }
        
        // Check closing signal
        if (this.isClosingSignal(content)) {
            logger.info('SILENCE_DETECTED', { reason: 'closing_signal' });
            return { shouldReply: false, reason: 'conversation_ending', action: 'let_die' };
        }
        
        // Check acknowledgment streak
        const streak = this.getAcknowledgmentStreak(contact.id, context);
        if (streak >= this.acknowledgmentStreakThreshold) {
            logger.info('SILENCE_DETECTED', { reason: 'ack_streak', streak });
            return { shouldReply: false, reason: 'acknowledgment_streak', streak, action: 'let_conversation_rest' };
        }
        
        // Check if it's a dead conversation (3+ back-and-forth of just acknowledgments)
        if (this.isDeadConversation(contact.id, context)) {
            return { shouldReply: false, reason: 'dead_conversation', action: 'let_die' };
        }
        
        // Check late night + non-urgent
        if (this.isLateNight() && !this.seemsUrgent(content)) {
            logger.info('SILENCE_DETECTED', { reason: 'late_night_non_urgent' });
            return { shouldReply: true, reason: 'late_night_but_replying_briefly', delay: true };
        }
        
        return { shouldReply: true, reason: 'normal_conversation' };
    }
    
    // ============================================
    // Detection Methods
    // ============================================
    isStandaloneAcknowledgment(content) {
        const trimmed = content.trim();
        return SILENCE_PATTERNS.standalone.some(pattern => pattern.test(trimmed));
    }
    
    isClosingSignal(content) {
        return SILENCE_PATTERNS.closingSignals.some(pattern => pattern.test(content));
    }
    
    hasOverride(content) {
        return OVERRIDE_TRIGGERS.some(pattern => pattern.test(content));
    }
    
    seemsUrgent(content) {
        const urgent = /\b(urgent|emergency|help me|please|asap|now now|quickly|important)\b/i;
        return urgent.test(content);
    }
    
    isLateNight() {
        const hour = new Date().getHours();
        return hour >= 0 && hour < 6;
    }
    
    // ============================================
    // Streak Detection
    // ============================================
    getAcknowledgmentStreak(contactId, context) {
        if (!context || context.length < 2) return 0;
        
        let streak = 0;
        // Check last exchanges (reverse order)
        const recent = [...context].reverse();
        
        for (const msg of recent) {
            if (this.isStandaloneAcknowledgment(msg.content || '')) {
                streak++;
            } else if ((msg.content || '').length > 15) {
                // Longer message breaks the streak
                break;
            }
        }
        
        return streak;
    }
    
    isDeadConversation(contactId, context) {
        if (!context || context.length < 6) return false; // Need at least 6 messages (3 exchanges)
        
        const recent = context.slice(-6); // Last 6 messages
        
        // Count how many are just acknowledgments
        const ackCount = recent.filter(m => this.isStandaloneAcknowledgment(m.content || '')).length;
        
        // If 4+ out of last 6 are just acknowledgments, conversation is dead
        return ackCount >= 4;
    }
    
    // ============================================
    // Track Exchange
    // ============================================
    trackExchange(contactId, message, reply) {
        if (!this.recentExchanges.has(contactId)) {
            this.recentExchanges.set(contactId, []);
        }
        
        const exchanges = this.recentExchanges.get(contactId);
        exchanges.push({
            timestamp: Date.now(),
            messageLength: (message.content || message).length,
            replyLength: (reply.content || reply).length,
            isAcknowledgment: this.isStandaloneAcknowledgment(message.content || message)
        });
        
        // Keep only recent
        if (exchanges.length > this.maxTrackedExchanges) {
            exchanges.shift();
        }
    }
    
    // ============================================
    // Smart Delay Calculator
    // ============================================
    calculateDelay(contact, content, contextLength) {
        const { Settings } = require('../utils/supabase');
        
        let baseDelay = 2000; // 2 seconds minimum
        
        // Adjust by message length (longer = more typing time)
        const contentLength = content.length;
        if (contentLength > 200) baseDelay += 3000;
        else if (contentLength > 100) baseDelay += 1500;
        else if (contentLength > 50) baseDelay += 800;
        
        // Adjust by relationship (closer = faster response)
        const relationshipDelays = {
            family: -500,
            close_friend: -300,
            business: 1000,
            acquaintance: 500,
            stranger: 1500
        };
        baseDelay += relationshipDelays[contact.relationship_type] || 0;
        
        // Longer context = takes more time to "read"
        if (contextLength > 10) baseDelay += 1000;
        
        // Add randomness (human-like)
        const randomFactor = 500 + Math.random() * 1500;
        baseDelay += randomFactor;
        
        // Ensure within bounds
        const min = Settings.get('typing_delay_min', 1000);
        const max = Settings.get('typing_delay_max', 8000);
        
        return Math.max(min, Math.min(max, baseDelay));
    }
    
    // Multi-message burst detection (when to split into multiple messages)
    shouldSplitMessage(content) {
        if (content.length < 100) return [content]; // Single short message
        
        // Split at sentence boundaries if long
        const sentences = content.match(/[^.!?]+[.!?]+/g) || [content];
        
        if (sentences.length >= 2 && content.length > 150) {
            // Split into 2-3 messages for natural feel
            const mid = Math.floor(sentences.length / 2);
            const first = sentences.slice(0, mid).join(' ').trim();
            const second = sentences.slice(mid).join(' ').trim();
            
            if (first.length > 20 && second.length > 20) {
                return [first, second];
            }
        }
        
        return [content];
    }
}

module.exports = new SilenceEngine();
