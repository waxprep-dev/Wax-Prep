// ============================================
// DAVID OS — Custom Rate Limiting
// Per-contact, per-endpoint, burst handling
// ============================================

const { logger } = require('../utils/logger');

// In-memory rate limiter (use Redis in production)
class RateLimiter {
    constructor() {
        this.windows = new Map();
        this.defaultWindow = 60000; // 1 minute
        this.defaultMax = 30;
    }

    check(key, windowMs = this.defaultWindow, maxRequests = this.defaultMax) {
        const now = Date.now();
        const windowKey = `${key}:${Math.floor(now / windowMs)}`;
        
        const current = this.windows.get(windowKey) || 0;
        
        if (current >= maxRequests) {
            return { allowed: false, retryAfter: windowMs - (now % windowMs) };
        }
        
        this.windows.set(windowKey, current + 1);
        
        // Cleanup old windows periodically
        if (Math.random() < 0.01) this.cleanup(now, windowMs);
        
        return { allowed: true, remaining: maxRequests - current - 1 };
    }

    cleanup(now, windowMs) {
        const cutoff = Math.floor(now / windowMs) - 1;
        for (const [key] of this.windows) {
            const windowId = parseInt(key.split(':').pop());
            if (windowId < cutoff) {
                this.windows.delete(key);
            }
        }
    }
}

const limiter = new RateLimiter();

// WhatsApp message rate limiter (prevent spam)
const messageLimiter = new RateLimiter();

function checkMessageRate(contactId) {
    return messageLimiter.check(`msg:${contactId}`, 60000, 20); // 20 msgs per minute per contact
}

function checkApiRate(endpoint, ip) {
    return limiter.check(`api:${endpoint}:${ip}`, 60000, 60); // 60 requests per minute
}

module.exports = { RateLimiter, limiter, checkMessageRate, checkApiRate };
