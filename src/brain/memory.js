// ============================================
// DAVID OS — Conversation Memory System
// Context windows, summarization, topic tracking
// ============================================

const { Messages, Conversations } = require('../utils/supabase');
const ai = require('../utils/groq');
const { logger } = require('../utils/logger');

class MemorySystem {
    constructor() {
        this.contextCache = new Map();
        this.summaryCache = new Map();
        this.maxContextMessages = parseInt(process.env.MAX_CONTEXT_MESSAGES) || 20;
        this.summaryThreshold = parseInt(process.env.CONVERSATION_SUMMARY_THRESHOLD) || 50;
    }
    
    // ============================================
    // Build Context for AI
    // ============================================
    async buildContext(contactId, options = {}) {
        const cacheKey = `${contactId}-${Date.now()}`; // Short cache
        
        // Get recent messages
        const messages = await Messages.getRecentContext(contactId, this.maxContextMessages);
        
        // Check if we need summarization
        const totalMessages = await this.getMessageCount(contactId);
        let summary = null;
        
        if (totalMessages > this.summaryThreshold && !options.skipSummary) {
            summary = await this.getOrCreateSummary(contactId);
        }
        
        // Build context array
        const context = [];
        
        // Add summary as first context if available
        if (summary) {
            context.push({
                role: 'system',
                content: `[Conversation Summary: ${summary}]`,
                isSummary: true
            });
        }
        
        // Add recent messages
        messages.forEach(msg => {
            context.push({
                role: msg.direction === 'inbound' ? 'user' : 'assistant',
                content: msg.content,
                timestamp: msg.created_at,
                sentiment: msg.sentiment,
                aiGenerated: msg.ai_generated
            });
        });
        
        // Extract topics and patterns
        const topics = this.extractTopics(messages);
        const patterns = this.detectPatterns(messages);
        
        return {
            messages: context,
            summary,
            topics,
            patterns,
            messageCount: totalMessages,
            lastInteraction: messages.length > 0 ? messages[messages.length - 1].created_at : null
        };
    }
    
    // ============================================
    // Conversation Summarization
    // ============================================
    async getOrCreateSummary(contactId) {
        // Check cache
        const cached = this.summaryCache.get(contactId);
        if (cached && Date.now() - cached.time < 300000) { // 5 min cache
            return cached.summary;
        }
        
        // Get conversation
        const conv = await Conversations.findOrCreate(contactId);
        
        // If summary is fresh, return it
        if (conv.summary_text && conv.summary_updated_at) {
            const hoursSince = (Date.now() - new Date(conv.summary_updated_at).getTime()) / 3600000;
            if (hoursSince < 1) {
                this.summaryCache.set(contactId, { summary: conv.summary_text, time: Date.now() });
                return conv.summary_text;
            }
        }
        
        // Generate new summary
        const summary = await this.generateSummary(contactId);
        
        // Update conversation
        await Conversations.updateContext(conv.id, []);
        await require('../utils/supabase').supabase
            .from('davidos_conversations')
            .update({ summary_text: summary, summary_updated_at: new Date().toISOString() })
            .eq('id', conv.id);
        
        this.summaryCache.set(contactId, { summary, time: Date.now() });
        return summary;
    }
    
    async generateSummary(contactId) {
        // Get older messages (not in context window)
        const { data: oldMessages } = await require('../utils/supabase').supabase
            .from('davidos_messages')
            .select('content, direction, created_at')
            .eq('contact_id', contactId)
            .order('created_at', { ascending: false })
            .range(this.maxContextMessages, this.maxContextMessages + 30);
        
        if (!oldMessages || oldMessages.length === 0) {
            return null;
        }
        
        const conversation = oldMessages.reverse().map(m => 
            `${m.direction === 'inbound' ? 'THEM' : 'DAVID'}: ${m.content}`
        ).join('\n');
        
        try {
            const summary = await ai.quick(
                `Summarize this conversation briefly. Capture key topics, decisions, and relationship context. Be concise:\n\n${conversation}`,
                'You create concise conversation summaries.',
                { maxTokens: 200 }
            );
            
            return summary.substring(0, 500);
        } catch (error) {
            logger.error('SUMMARY_ERROR', { error: error.message, contactId });
            return null;
        }
    }
    
    // ============================================
    // Topic Extraction
    // ============================================
    extractTopics(messages) {
        const topics = new Set();
        const text = messages.map(m => m.content).join(' ').toLowerCase();
        
        // Common topic patterns
        const topicPatterns = {
            'work': /\b(work|job|office|boss|colleague|project|deadline|client)\b/,
            'money': /\b(money|payment|salary|income|debt|loan|budget|expensive|cheap|price|cost)\b/,
            'family': /\b(family|mama|papa|mum|dad|brother|sister|wife|husband|child|cousin|uncle|aunt)\b/,
            'health': /\b(health|sick|hospital|doctor|medicine|pain|wellness|fitness|gym)\b/,
            'relationship': /\b(love|dating|girlfriend|boyfriend|relationship|breakup|wedding|marriage)\b/,
            'tech': /\b(phone|laptop|app|software|internet|wifi|data|computer|tech|code)\b/,
            'food': /\b(food|eat|restaurant|cook|rice|swallow|soup|chop|hungry)\b/,
            'travel': /\b(travel|trip|flight|airport|hotel|vacation|lagos|abuja|nigeria|abroad)\b/,
            'entertainment': /\b(music|movie|film|song|artist|concert|party|club|fun)\b/,
            'business': /\b(business|startup|company|invest|profit|revenue|deal|contract)\b/,
            'education': /\b(school|university|exam|course|study|degree|student|learn)\b/,
            'spiritual': /\b(church|prayer|god|pastor|bless|faith|amen|service|worship)\b/,
            'sports': /\b(football|soccer|match|game|team|player|premier league|epl|champions league)\b/,
            'politics': /\b(politics|government|election|president|governor|minister|vote)\b/
        };
        
        Object.entries(topicPatterns).forEach(([topic, pattern]) => {
            if (pattern.test(text)) topics.add(topic);
        });
        
        return Array.from(topics);
    }
    
    // ============================================
    // Pattern Detection
    // ============================================
    detectPatterns(messages) {
        if (messages.length < 3) return {};
        
        const patterns = {
            responseTimeAvg: 0,
            davidInitiated: 0,
            otherInitiated: 0,
            avgMessageLength: 0,
            questionFrequency: 0,
            emojiUsage: 0
        };
        
        let totalResponseTime = 0;
        let responseCount = 0;
        let totalLength = 0;
        let questionCount = 0;
        let emojiCount = 0;
        
        for (let i = 0; i < messages.length; i++) {
            const msg = messages[i];
            totalLength += (msg.content || '').length;
            
            if ((msg.content || '').includes('?')) questionCount++;
            emojiCount += ((msg.content || '').match(/[\u{1F600}-\u{1F64F}]/gu) || []).length;
            
            if (msg.direction === 'inbound') {
                patterns.otherInitiated++;
            } else {
                patterns.davidInitiated++;
            }
            
            // Calculate response times
            if (i > 0 && msg.direction !== messages[i-1].direction) {
                const time = new Date(msg.created_at).getTime() - new Date(messages[i-1].created_at).getTime();
                if (time > 0 && time < 86400000) { // Less than 1 day
                    totalResponseTime += time;
                    responseCount++;
                }
            }
        }
        
        patterns.avgMessageLength = Math.round(totalLength / messages.length);
        patterns.questionFrequency = Math.round((questionCount / messages.length) * 100);
        patterns.emojiUsage = emojiCount;
        patterns.responseTimeAvg = responseCount > 0 ? Math.round(totalResponseTime / responseCount / 1000) : 0; // seconds
        
        return patterns;
    }
    
    // ============================================
    // Message Count
    // ============================================
    async getMessageCount(contactId) {
        const { count } = await require('../utils/supabase').supabase
            .from('davidos_messages')
            .select('*', { count: 'exact', head: true })
            .eq('contact_id', contactId);
        return count || 0;
    }
    
    // ============================================
    // Conversation Insights
    // ============================================
    async getInsights(contactId) {
        const messages = await Messages.getByContact(contactId, { limit: 100 });
        
        const inbound = messages.filter(m => m.direction === 'inbound');
        const outbound = messages.filter(m => m.direction === 'outbound');
        
        const sentiments = inbound.reduce((acc, m) => {
            if (m.sentiment) acc[m.sentiment] = (acc[m.sentiment] || 0) + 1;
            return acc;
        }, {});
        
        const emotions = inbound.reduce((acc, m) => {
            if (m.emotion) acc[m.emotion] = (acc[m.emotion] || 0) + 1;
            return acc;
        }, {});
        
        return {
            totalMessages: messages.length,
            ratio: {
                david: outbound.length,
                them: inbound.length
            },
            sentiments,
            emotions,
            topics: this.extractTopics(messages),
            patterns: this.detectPatterns(messages)
        };
    }
    
    // ============================================
    // Clear cache for a contact
    // ============================================
    invalidate(contactId) {
        this.contextCache.delete(contactId);
        this.summaryCache.delete(contactId);
    }
    
    // Global cache clear
    clearAll() {
        this.contextCache.clear();
        this.summaryCache.clear();
    }
}

module.exports = new MemorySystem();
