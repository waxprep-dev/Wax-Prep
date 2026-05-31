// ============================================
// DAVID OS — Escalation Engine
// When to wake David up. Multi-tier alerting.
// ============================================

const { Escalations, Settings } = require('../utils/supabase');
const { logger } = require('../utils/logger');

// Escalation triggers with severity scoring
const ESCALATION_TRIGGERS = {
    // EMERGENCY (Critical)
    emergency: {
        keywords: ['emergency', 'urgent help', 'hospital', 'accident', 'police', 'fire', 'ambulance', 'dying', 'death', 'someone died', 'blood', 'stabbed', 'shot'],
        severity: 'critical',
        category: 'emergency',
        score: 10,
        immediate: true
    },
    
    // EMOTIONAL CRISIS (Critical)
    emotional_crisis: {
        keywords: ['suicide', 'kill myself', 'end my life', 'self harm', 'depressed', 'hopeless', 'can\'t go on', 'no reason to live'],
        severity: 'critical',
        category: 'emotional_crisis',
        score: 10,
        immediate: true
    },
    
    // FINANCIAL (High)
    financial: {
        keywords: ['pay me', 'send money', 'urgent payment', 'wire transfer', 'bank details', 'account number', 'suspicious transaction'],
        severity: 'high',
        category: 'money',
        score: 7,
        immediate: false
    },
    
    // LARGE DEALS (High)
    big_deal: {
        keywords: [], // Detected by amount parsing
        severity: 'high',
        category: 'money',
        score: 6,
        immediate: false,
        detectByAmount: true,
        amountThreshold: 50000 // Naira
    },
    
    // PRIVACY (High)
    privacy: {
        keywords: ['your address', 'where do you live', 'your location', 'personal information', 'private info', 'who are you'],
        severity: 'high',
        category: 'privacy',
        score: 6,
        immediate: false
    },
    
    // REPEATED CONTACT (Medium)
    repeated_contact: {
        detectByCount: true,
        countThreshold: 5,
        timeWindow: 3600000, // 1 hour
        severity: 'medium',
        category: 'repeated_contact',
        score: 5,
        immediate: false
    },
    
    // AI CONFUSION (Medium)
    ai_confused: {
        keywords: ['are you a bot', 'is this ai', 'are you automated', 'chatbot', 'not making sense', 'you don\'t understand'],
        severity: 'medium',
        category: 'ai_confused',
        score: 4,
        immediate: false
    },
    
    // BUSINESS URGENT (Medium)
    business_urgent: {
        keywords: ['deadline', 'asap', 'urgent meeting', 'crisis', 'problem with project', 'client angry', 'complaint'],
        severity: 'medium',
        category: 'business',
        score: 4,
        immediate: false
    },
    
    // NEW PERSONAL QUESTIONS (Low-Medium)
    personal_inquiry: {
        keywords: ['your wife', 'your girlfriend', 'your family', 'your house', 'your car', 'how old are you', 'your age'],
        severity: 'low',
        category: 'privacy',
        score: 3,
        immediate: false
    }
};

class EscalationEngine {
    constructor() {
        this.messageCounts = new Map(); // contactId -> [{timestamp}]
        this.recentEscalations = new Map(); // contactId -> timestamp
        this.cooldownPeriod = 300000; // 5 min between escalations for same contact
    }
    
    // ============================================
    // Main Check: Should we escalate?
    // ============================================
    async check(message, contact, context = [], aiConfidence = 0.5) {
        const content = (message.content || message).toLowerCase();
        const triggers = [];
        
        // Check all trigger types
        for (const [type, config] of Object.entries(ESCALATION_TRIGGERS)) {
            let triggered = false;
            
            if (config.keywords && config.keywords.length > 0) {
                triggered = config.keywords.some(kw => content.includes(kw));
            }
            
            if (config.detectByAmount) {
                triggered = this.checkAmountThreshold(content, config.amountThreshold);
            }
            
            if (config.detectByCount) {
                triggered = this.checkMessageFrequency(contact.id, config.countThreshold, config.timeWindow);
            }
            
            if (triggered) {
                triggers.push({ type, ...config });
            }
        }
        
        // Check AI confusion (3+ exchanges of confusion)
        if (this.detectConfusion(context)) {
            triggers.push({
                type: 'ai_confused',
                severity: 'medium',
                category: 'ai_confused',
                score: 4
            });
        }
        
        // Check low confidence
        if (aiConfidence < 0.4) {
            triggers.push({
                type: 'low_confidence',
                severity: 'medium',
                category: 'system_error',
                score: 4,
                details: { confidence: aiConfidence }
            });
        }
        
        // Sort by severity
        triggers.sort((a, b) => b.score - a.score);
        
        if (triggers.length === 0) {
            return { escalated: false, triggers: [] };
        }
        
        // Get highest severity trigger
        const primary = triggers[0];
        
        // Check cooldown
        if (this.isInCooldown(contact.id)) {
            logger.info('ESCALATION_COOLDOWN', { contactId: contact.id, trigger: primary.type });
            return { escalated: false, triggers, inCooldown: true };
        }
        
        // Check if emergency alerting is enabled
        const emergencyEnabled = await Settings.get('emergency_alert', true);
        if (primary.severity === 'critical' && !emergencyEnabled) {
            return { escalated: false, triggers, disabled: true };
        }
        
        // Create escalation record
        const escalation = await this.createEscalation(contact, message, primary, triggers);
        
        // Set cooldown
        this.recentEscalations.set(contact.id, Date.now());
        
        // Send notifications if critical/high
        if (primary.severity === 'critical' || primary.severity === 'high') {
            await this.sendAlert(contact, message, escalation, primary);
        }
        
        return {
            escalated: true,
            escalation,
            triggers,
            primary,
            immediate: primary.immediate || primary.severity === 'critical'
        };
    }
    
    // ============================================
    // Amount Detection (Naira)
    // ============================================
    checkAmountThreshold(content, threshold) {
        // Match patterns like: 50000, 50,000, 50k, ₦50000, 50000 naira
        const patterns = [
            /[₦N]\s*(\d[\d,]*(?:\.\d+)?)\s*(?:naira)?/i,
            /(\d[\d,]*(?:\.\d+)?)\s*(?:naira|k\b|thousand|million)/i,
            /\b(\d{5,})\s*(?:naira)?\b/i
        ];
        
        for (const pattern of patterns) {
            const match = content.match(pattern);
            if (match) {
                const amount = parseFloat(match[1].replace(/,/g, ''));
                if (match[0].includes('million')) return amount * 1000000 >= threshold;
                if (match[0].includes('k') || match[0].includes('thousand')) return amount * 1000 >= threshold;
                return amount >= threshold;
            }
        }
        
        return false;
    }
    
    // ============================================
    // Message Frequency Check
    // ============================================
    checkMessageFrequency(contactId, threshold, timeWindow) {
        if (!this.messageCounts.has(contactId)) {
            this.messageCounts.set(contactId, []);
        }
        
        const now = Date.now();
        const counts = this.messageCounts.get(contactId);
        
        // Add current message
        counts.push(now);
        
        // Clean old messages
        const cutoff = now - timeWindow;
        const recent = counts.filter(t => t > cutoff);
        this.messageCounts.set(contactId, recent);
        
        return recent.length >= threshold;
    }
    
    // ============================================
    // Confusion Detection
    // ============================================
    detectConfusion(context) {
        if (!context || context.length < 6) return false;
        
        // Check last 6 messages for confusion patterns
        const recent = context.slice(-6);
        const confusionPatterns = [
            /\b(don't understand|confused|what do you mean|not making sense|huh\?|what\?|repeat)\b/i,
            /\b(are you listening|you're not|that's wrong|incorrect|not right)\b/i
        ];
        
        let confusionCount = 0;
        for (const msg of recent) {
            const content = (msg.content || '').toLowerCase();
            if (confusionPatterns.some(p => p.test(content))) {
                confusionCount++;
            }
        }
        
        // 3+ confusion expressions in last 6 messages
        return confusionCount >= 3;
    }
    
    // ============================================
    // Cooldown Check
    // ============================================
    isInCooldown(contactId) {
        const lastEscalation = this.recentEscalations.get(contactId);
        if (!lastEscalation) return false;
        return (Date.now() - lastEscalation) < this.cooldownPeriod;
    }
    
    // ============================================
    // Create Escalation Record
    // ============================================
    async createEscalation(contact, message, primary, allTriggers) {
        try {
            const escalation = await Escalations.create({
                contact_id: contact.id,
                message_id: message.id || null,
                reason: primary.type,
                severity: primary.severity,
                category: primary.category,
                details: {
                    all_triggers: allTriggers.map(t => t.type),
                    message_preview: (message.content || message).substring(0, 200),
                    ai_confidence: message.aiConfidence
                },
                resolved: false,
                auto_escalated: true
            });
            
            logger.escalation(primary.type, primary.severity, contact.id, {
                category: primary.category,
                triggers: allTriggers.map(t => t.type)
            });
            
            return escalation;
        } catch (error) {
            logger.error('ESCALATION_CREATE_ERROR', { error: error.message, contactId: contact.id });
            return null;
        }
    }
    
    // ============================================
    // Send Alert (Critical/High only)
    // ============================================
    async sendAlert(contact, message, escalation, trigger) {
        const alerts = [];
        
        // Prepare alert payload
        const alertPayload = {
            type: 'escalation',
            severity: trigger.severity,
            category: trigger.category,
            contact: {
                name: contact.name || 'Unknown',
                phone: contact.phone_number,
                relationship: contact.relationship_type
            },
            message_preview: (message.content || message).substring(0, 100),
            escalation_id: escalation?.id,
            timestamp: new Date().toISOString(),
            action_required: trigger.immediate ? 'IMMEDIATE' : 'REVIEW'
        };
        
        // TODO: Implement actual notification channels
        // - WebSocket push to dashboard
        // - Slack webhook
        // - Email
        // - SMS via Twilio for critical
        
        logger.info('ALERT_SENT', alertPayload);
        
        return alerts;
    }
    
    // ============================================
    // Get Stats
    // ============================================
    async getStats(period = 'today') {
        const escalations = await Escalations.list({ resolved: false });
        
        const bySeverity = { critical: 0, high: 0, medium: 0, low: 0 };
        const byCategory = {};
        
        escalations.forEach(e => {
            bySeverity[e.severity] = (bySeverity[e.severity] || 0) + 1;
            byCategory[e.category] = (byCategory[e.category] || 0) + 1;
        });
        
        return {
            total: escalations.length,
            unresolved: escalations.filter(e => !e.resolved).length,
            bySeverity,
            byCategory,
            recent: escalations.slice(0, 10)
        };
    }
}

module.exports = new EscalationEngine();
