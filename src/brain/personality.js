// ============================================
// DAVID OS — Personality Engine
// The soul of David. 5 layers + dynamic adaptation
// ============================================

const { Personality, Settings } = require('../utils/supabase');
const { logger } = require('../utils/logger');

// Nigerian context enrichments
const NIGERIAN_CONTEXT = {
    greetings: ['How far?', 'How body?', 'Wetin dey happen?', 'You do well', 'Well done sir/ma'],
    closers: ['Make I run', 'I dey come', 'Later nau', 'We go see', 'Oya bye'],
    fillers: ['sha', 'nko', 'jare', 'sef', 'na', 'dey', 'abi'],
    affirmations: ['Ehen', 'Okay nau', 'No wahala', 'I hear', 'True talk'],
    reactions: {'happy': '💯🙏', 'excited': '🚀💯', 'agreement': '👊💯', 'sympathy': '❤️🙏'},
    timeGreetings: {
        morning: ['Morning! 🌅', 'How was your night?', 'Hope you slept well'],
        afternoon: ['Afternoon', 'How\'s the day going?'],
        evening: ['Evening', 'How far?'],
        night: ['You still dey awake? 😄', 'Night night']
    }
};

// Slang intensity by relationship
const SLANG_INTENSITY = {
    family: 0.3,
    close_friend: 0.9,
    business: 0.1,
    acquaintance: 0.2,
    stranger: 0.05
};

class PersonalityEngine {
    constructor() {
        this.cache = new Map();
        this.cacheExpiry = 5 * 60 * 1000; // 5 min
        this.defaultPersonality = this.getDefaultPersonality();
    }
    
    // ============================================
    // Main Builder
    // ============================================
    async buildContext(contact, message, conversationContext = []) {
        const startTime = Date.now();
        
        // Get personality layer
        const layer = contact.relationship_type || 'stranger';
        const personality = await this.getPersonality(layer);
        
        // Get current settings
        const settings = await Settings.getAll();
        
        // Detect context signals
        const signals = await this.detectSignals(message, conversationContext);
        
        // Build the complete system prompt
        const systemPrompt = this.constructSystemPrompt(personality, contact, settings, signals);
        
        // Build conversation history
        const history = this.buildHistory(conversationContext, personality);
        
        // Add current message
        const messages = [
            { role: 'system', content: systemPrompt },
            ...history,
            { role: 'user', content: message.content || message }
        ];
        
        logger.aiDecision({
            action: 'personality_build',
            layer,
            signals: Object.keys(signals).filter(k => signals[k]),
            duration: Date.now() - startTime
        });
        
        return {
            messages,
            personality,
            signals,
            layer,
            config: {
                temperature: this.getTemperature(personality, signals),
                maxTokens: this.getMaxTokens(personality, signals),
                topP: 0.9
            }
        };
    }
    
    // ============================================
    // Personality Retrieval
    // ============================================
    async getPersonality(layer) {
        // Check cache
        const cached = this.cache.get(layer);
        if (cached && Date.now() - cached.fetched < this.cacheExpiry) {
            return cached.data;
        }
        
        // Fetch from DB
        let personality = await Personality.getByLayer(layer);
        
        if (!personality) {
            personality = this.defaultPersonality[layer] || this.defaultPersonality.stranger;
        }
        
        this.cache.set(layer, { data: personality, fetched: Date.now() });
        return personality;
    }
    
    // ============================================
    // Signal Detection
    // ============================================
    async detectSignals(message, context) {
        const content = (message.content || message).toLowerCase();
        const signals = {
            // Financial
            isNegotiation: /\b(price|cost|budget|pay|payment|naira|\₦|discount|quote|invoice|fee|charge|billing|amount)\b/i.test(content),
            isMoneyDiscussion: /\b(\₦|naira|\$|€|£|\d+k|\d+,?\d+\s*(naira|k|thousand|million))\b/i.test(content),
            
            // Emotional
            isEmergency: /\b(emergency|urgent|hospital|accident|police|fire|ambulance|help me|dying|dead|death|killed)\b/i.test(content),
            isDistressed: /\b(sad|depressed|suicide|hurt|pain|crying|heartbroken|devastated|lost everything)\b/i.test(content),
            isAngry: /\b(angry|furious|stupid|useless|idiot|terrible|worst|hate|annoying|frustrated)\b/i.test(content),
            isExcited: /\b(excited|amazing|awesome|fantastic|incredible|won|celebrate|promoted|engaged|married|baby)\b/i.test(content),
            
            // Social
            isGreeting: /^(hi|hello|hey|good morning|good afternoon|good evening|how far|how body|wetin dey|yo|what's up|sup)\b/i.test(content),
            isQuestion: /\?/.test(content) || /\b(what|where|when|why|how|who|which)\b/i.test(content),
            isGoodbye: /\b(bye|goodbye|see you|later|talk soon|cya|night)\b/i.test(content),
            isAcknowledgment: /^(ok|okay|seen|alright|cool|noted|lol|haha|👍|💯|nice|got it|bet|aight)$/i.test(content.trim()),
            
            // Intent
            isBusinessRequest: /\b(meeting|schedule|appointment|call|zoom|discuss|proposal|contract|deal|partnership)\b/i.test(content),
            isPersonal: /\b(family|mama|papa|brother|sister|wife|husband|child|personal|private)\b/i.test(content),
            
            // Language
            hasPidgin: /\b(dey|na|wahala|abeg|oya|shey|nko|jare|sha|sef|omo|guy|baba)\b/i.test(content),
            hasYoruba: /\b(e ku|e se|ba wo ni|daadaa|o dabaa|sugbon|nitori|fun|ati|ni)\b/i.test(content),
            hasIgbo: /\b(nee nu|daalu|kedu|oma|o di|nne|nna)\b/i.test(content),
            hasHausa: /\b(nagode|sannu|yauwa|toh|ai|ba|da|na)\b/i.test(content),
            
            // Media
            hasImage: message.content_type === 'image' || content.includes('[image'),
            hasVoice: message.content_type === 'voice' || content.includes('[voice'),
            
            // Time
            isLateNight: this.isLateNight(),
            isWeekend: this.isWeekend(),
            isSunday: this.isSunday()
        };
        
        // Urgency calculation
        signals.urgencyScore = this.calculateUrgency(signals);
        signals.shouldUsePidgin = signals.hasPidgin || layerIntensity(contactFromContext) > 0.5;
        
        return signals;
    }
    
    // ============================================
    // System Prompt Construction
    // ============================================
    constructSystemPrompt(personality, contact, settings, signals) {
        const parts = [];
        
        // Core identity
        parts.push(`You are David's AI assistant. You are NOT David — you are his digital twin.`);
        parts.push(`Your job: Handle WhatsApp conversations naturally so David doesn't have to reply to everything.`);
        
        // Personality layer
        parts.push(`\n=== PERSONALITY MODE: ${personality.layer?.toUpperCase()} ===`);
        parts.push(personality.system_prompt || personality.prompt_text);
        
        // Nigerian identity
        parts.push(`\n=== IDENTITY ===`);
        parts.push(`- You are a Nigerian. Educated but relatable.`);
        parts.push(`- You naturally mix Nigerian English with standard English.`);
        parts.push(`- You understand Nigerian context: hustle culture, respect for elders, family bonds.`);
        
        // Language rules
        parts.push(`\n=== LANGUAGE RULES ===`);
        const slangLevel = SLANG_INTENSITY[contact.relationship_type] || 0.2;
        parts.push(`- Slang intensity: ${Math.round(slangLevel * 100)}%`);
        
        if (slangLevel > 0.5) {
            parts.push(`- Freely use Pidgin: "dey", "na", "wahala", "abeg", "oya", "shey", "nko", "jare", "sha", "sef"`);
            parts.push(`- Use "bro" freely with peers`);
            parts.push(`- Can tease and joke`);
        } else if (slangLevel > 0.2) {
            parts.push(`- Light Pidgin is okay: "dey", "na", "abeg"`);
            parts.push(`- Use "sir/ma" for respect`);
        } else {
            parts.push(`- Use standard English primarily`);
            parts.push(`- Minimal slang, maximum professionalism`);
            parts.push(`- "Sir/Ma" for respect with elders`);
        }
        
        // Response rules
        parts.push(`\n=== RESPONSE RULES ===`);
        parts.push(`- SHORT messages: 1-3 lines max, ${settings.max_message_length || 500} chars max`);
        parts.push(`- Sometimes send 2-3 quick messages in a row (like a real person)`);
        parts.push(`- Use emojis naturally: ${personality.emoji_frequency > 0.4 ? '🙏💯😂🤝❤️👊🚀' : 'occasional 🙏 💯'}`);
        parts.push(`- NEVER write essays. Be concise.`);
        parts.push(`- Match the energy of the incoming message`);
        parts.push(`- Ask follow-up questions to keep conversation going`);
        
        // Context signals
        parts.push(`\n=== CURRENT CONTEXT ===`);
        if (signals.isLateNight) parts.push(`- It's late night. Be brief. Only reply if urgent.`);
        if (signals.isSunday) parts.push(`- It's Sunday. More relaxed tone.`);
        if (signals.isNegotiation) parts.push(`- NEGOTIATION MODE: Never agree immediately. Ask questions. Say "Let me check and get back to you."`);
        if (signals.isEmergency) parts.push(`- EMERGENCY detected: Be calm, supportive, offer immediate help.`);
        if (signals.isDistressed) parts.push(`- Person seems distressed: Gentle, supportive, offer to call.`);
        if (signals.isAngry) parts.push(`- Person seems angry: Stay calm, don't argue, de-escalate.`);
        if (signals.isExcited) parts.push(`- Person is excited: Match energy, celebrate with them!`);
        
        // Silence intelligence
        parts.push(`\n=== SILENCE RULES ===`);
        parts.push(`- Do NOT reply to: "ok", "seen", "lol", "haha", "cool", "noted", "alright", "👍", "💯" as standalone`);
        parts.push(`- Do NOT reply if last 3 exchanges were just acknowledgments`);
        parts.push(`- Let conversations die naturally`);
        
        // Self-revelation
        parts.push(`\n=== IDENTITY REVEAL ===`);
        parts.push(`- DEFAULT: NEVER say you are AI`);
        parts.push(`- ONLY reveal if: directly asked "Are you a bot?", confusion after 3+ exchanges, or Ghost Mode ON`);
        parts.push(`- If revealing: "I'm an AI assistant David set up. He'll reply personally if needed. But I can help with most things."`);
        
        // Contact info
        parts.push(`\n=== TALKING TO ===`);
        parts.push(`- Name: ${contact.name || 'Unknown'}`);
        parts.push(`- Relationship: ${contact.relationship_type || 'stranger'}`);
        parts.push(`- Trust Level: ${contact.trust_level || 50}/100`);
        if (contact.notes) parts.push(`- Notes: ${contact.notes}`);
        
        return parts.join('\n');
    }
    
    // ============================================
    // History Builder
    // ============================================
    buildHistory(context, personality) {
        if (!context || context.length === 0) return [];
        
        // Take last N messages
        const maxContext = 20;
        const recent = context.slice(-maxContext);
        
        return recent.map(msg => ({
            role: msg.direction === 'inbound' ? 'user' : 'assistant',
            content: msg.content
        }));
    }
    
    // ============================================
    // Temperature & Token Control
    // ============================================
    getTemperature(personality, signals) {
        let temp = 0.7;
        
        if (signals.isNegotiation) temp = 0.4; // More predictable
        if (signals.isEmergency) temp = 0.3; // Very focused
        if (signals.isExcited) temp = 0.8; // More creative
        if (personality.layer === 'close_friend') temp = 0.85; // More playful
        if (personality.layer === 'business') temp = 0.5; // More controlled
        
        return Math.min(temp, 1.0);
    }
    
    getMaxTokens(personality, signals) {
        let tokens = 150; // Default short
        
        if (signals.isNegotiation) tokens = 200;
        if (signals.isEmergency) tokens = 100;
        if (signals.isBusinessRequest) tokens = 180;
        if (personality.layer === 'business') tokens = 200;
        if (personality.layer === 'family') tokens = 120;
        
        return tokens;
    }
    
    // ============================================
    // Urgency Calculation
    // ============================================
    calculateUrgency(signals) {
        let score = 0;
        if (signals.isEmergency) score += 10;
        if (signals.isDistressed) score += 8;
        if (signals.isAngry) score += 5;
        if (signals.isNegotiation) score += 4;
        if (signals.isBusinessRequest) score += 3;
        if (signals.isExcited) score += 1;
        if (signals.isQuestion) score += 2;
        return Math.min(score, 10);
    }
    
    // ============================================
    // Time Helpers
    // ============================================
    isLateNight() {
        const hour = new Date().getHours();
        return hour >= 0 && hour < 6;
    }
    
    isWeekend() {
        const day = new Date().getDay();
        return day === 0 || day === 6;
    }
    
    isSunday() {
        return new Date().getDay() === 0;
    }
    
    // ============================================
    // Post-processing
    // ============================================
    postProcessResponse(response, personality, signals) {
        let text = response.content || response;
        
        // Remove any AI self-references that slipped through
        text = text.replace(/\b(as an AI|I'm an AI|as a language model|I don't have feelings|I don't have personal|I cannot physically)\b/gi, '');
        
        // Ensure proper length
        const maxLen = personality.avg_response_length * 3 || 500;
        if (text.length > maxLen) {
            text = text.substring(0, maxLen).replace(/\s+\S*$/, '...');
        }
        
        // Add natural feel for close friends
        const slangLevel = SLANG_INTENSITY[personality.layer] || 0.2;
        if (slangLevel > 0.6 && !signals.isBusinessRequest && !signals.isEmergency) {
            // Sometimes lowercase for casual feel
            if (Math.random() > 0.7 && text.length < 30) {
                text = text.toLowerCase();
            }
        }
        
        // Clean up multiple spaces
        text = text.replace(/\s+/g, ' ').trim();
        
        return text;
    }
    
    // ============================================
    // Default Fallbacks
    // ============================================
    getDefaultPersonality() {
        return {
            family: {
                layer: 'family',
                prompt_text: 'Warm, respectful, caring family member',
                system_prompt: 'You are David talking to family. Warm, respectful, caring.',
                emoji_frequency: 0.4,
                formality_score: 70,
                humor_level: 30
            },
            close_friend: {
                layer: 'close_friend',
                prompt_text: 'Playful, energetic, loyal friend',
                system_prompt: 'You are David with close friends. Maximum vibes.',
                emoji_frequency: 0.6,
                formality_score: 20,
                humor_level: 85
            },
            business: {
                layer: 'business',
                prompt_text: 'Sharp, professional, strategic',
                system_prompt: 'You are David in business mode. Sharp and professional.',
                emoji_frequency: 0.2,
                formality_score: 85,
                humor_level: 20
            },
            acquaintance: {
                layer: 'acquaintance',
                prompt_text: 'Polite, helpful, approachable',
                system_prompt: 'You are David with acquaintances. Polite and helpful.',
                emoji_frequency: 0.2,
                formality_score: 60,
                humor_level: 40
            },
            stranger: {
                layer: 'stranger',
                prompt_text: 'Brief, polite, cautious',
                system_prompt: 'You are David with strangers. Brief and polite.',
                emoji_frequency: 0.1,
                formality_score: 75,
                humor_level: 10
            }
        };
    }
    
    clearCache() {
        this.cache.clear();
    }
}

// Helper for context
function layerIntensity(contact) {
    if (!contact) return 0.2;
    return SLANG_INTENSITY[contact.relationship_type] || 0.2;
}

module.exports = new PersonalityEngine();
