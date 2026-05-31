// ============================================
// DAVID OS — Groq AI Client
// LLM orchestration, cost tracking, retries
// ============================================

const Groq = require('groq-sdk');
const { logger } = require('./logger');
const { Costs } = require('./supabase');

const groq = new Groq({
    apiKey: process.env.GROQ_API_KEY
});

// Available models with pricing
const MODELS = {
    'llama-3.3-70b-versatile': { input: 0.59, output: 0.79, maxTokens: 8192 },
    'llama-3.1-8b-instant': { input: 0.05, output: 0.08, maxTokens: 8192 },
    'mixtral-8x7b-32768': { input: 0.24, output: 0.24, maxTokens: 32768 },
    'gemma2-9b-it': { input: 0.20, output: 0.20, maxTokens: 8192 },
    'llama-3.1-70b-versatile': { input: 0.59, output: 0.79, maxTokens: 8192 }
};

const DEFAULT_MODEL = process.env.GROQ_MODEL || 'llama-3.3-70b-versatile';
const MAX_RETRIES = 3;
const RETRY_DELAY = 1000;

class AIClient {
    constructor() {
        this.requestCount = 0;
        this.errorCount = 0;
        this.totalCost = 0;
        this.lastError = null;
        this.isHealthy = true;
    }
    
    // ============================================
    // Core Chat Completion
    // ============================================
    async chat(messages, options = {}) {
        const startTime = Date.now();
        const model = options.model || DEFAULT_MODEL;
        const modelConfig = MODELS[model] || MODELS[DEFAULT_MODEL];
        
        for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
            try {
                const completion = await groq.chat.completions.create({
                    messages,
                    model,
                    temperature: options.temperature ?? 0.7,
                    max_tokens: options.maxTokens || modelConfig.maxTokens,
                    top_p: options.topP || 0.9,
                    frequency_penalty: options.frequencyPenalty || 0.3,
                    presence_penalty: options.presencePenalty || 0.2,
                    stop: options.stop || null,
                    response_format: options.responseFormat || { type: 'text' }
                });
                
                const duration = Date.now() - startTime;
                const usage = completion.usage;
                const cost = this.calculateCost(model, usage?.prompt_tokens || 0, usage?.completion_tokens || 0);
                
                // Track cost
                this.totalCost += cost;
                this.requestCount++;
                this.isHealthy = true;
                
                // Async cost tracking (don't block)
                if (process.env.COST_TRACKING_ENABLED === 'true') {
                    Costs.track({
                        service: 'groq',
                        operation: options.operation || 'chat_completion',
                        model,
                        input_tokens: usage?.prompt_tokens || 0,
                        output_tokens: usage?.completion_tokens || 0,
                        cost_usd: cost,
                        request_duration_ms: duration,
                        contact_id: options.contactId || null,
                        message_id: options.messageId || null,
                        success: true
                    }).catch(err => logger.error('Cost tracking failed', { error: err.message }));
                }
                
                logger.info('GROQ_REQUEST', {
                    model,
                    duration,
                    cost,
                    tokensIn: usage?.prompt_tokens,
                    tokensOut: usage?.completion_tokens,
                    attempt
                });
                
                return {
                    content: completion.choices[0].message.content,
                    usage,
                    cost,
                    duration,
                    model,
                    finishReason: completion.choices[0].finish_reason
                };
                
            } catch (error) {
                this.lastError = error.message;
                this.errorCount++;
                
                const isRetryable = error.status === 429 || error.status >= 500 || error.code === 'ECONNRESET';
                
                if (attempt < MAX_RETRIES && isRetryable) {
                    const delay = RETRY_DELAY * attempt;
                    logger.warn(`GROQ_RETRY: Attempt ${attempt}/${MAX_RETRIES}, delaying ${delay}ms`, { error: error.message });
                    await this.sleep(delay);
                    continue;
                }
                
                logger.error('GROQ_ERROR', {
                    attempt,
                    model,
                    error: error.message,
                    status: error.status
                });
                
                this.isHealthy = false;
                
                // Return graceful fallback
                return {
                    content: this.getFallbackResponse(options.fallbackType),
                    usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
                    cost: 0,
                    duration: Date.now() - startTime,
                    model,
                    error: error.message,
                    fallback: true
                };
            }
        }
    }
    
    // ============================================
    // Structured Output (JSON mode)
    // ============================================
    async structuredChat(messages, schema, options = {}) {
        const systemPrompt = `You must respond with valid JSON only. Follow this schema exactly: ${JSON.stringify(schema)}. No other text.`;
        
        const allMessages = [
            { role: 'system', content: systemPrompt },
            ...messages
        ];
        
        const response = await this.chat(allMessages, {
            ...options,
            responseFormat: { type: 'json_object' },
            temperature: options.temperature || 0.3 // Lower temp for structured output
        });
        
        try {
            return {
                ...response,
                data: JSON.parse(response.content)
            };
        } catch (e) {
            logger.error('JSON_PARSE_ERROR', { content: response.content, error: e.message });
            return {
                ...response,
                data: null,
                parseError: e.message
            };
        }
    }
    
    // ============================================
    // Quick Completion (for simple tasks)
    // ============================================
    async quick(prompt, systemPrompt = null, options = {}) {
        const messages = [];
        if (systemPrompt) messages.push({ role: 'system', content: systemPrompt });
        messages.push({ role: 'user', content: prompt });
        
        // Use fast model for quick tasks
        const response = await this.chat(messages, {
            model: 'llama-3.1-8b-instant',
            maxTokens: options.maxTokens || 256,
            ...options
        });
        
        return response.content;
    }
    
    // ============================================
    // Streaming (for real-time dashboard updates)
    // ============================================
    async *stream(messages, options = {}) {
        const model = options.model || DEFAULT_MODEL;
        
        const stream = await groq.chat.completions.create({
            messages,
            model,
            temperature: options.temperature ?? 0.7,
            max_tokens: options.maxTokens || 1024,
            stream: true
        });
        
        for await (const chunk of stream) {
            const content = chunk.choices[0]?.delta?.content || '';
            if (content) yield content;
        }
    }
    
    // ============================================
    // Sentiment Analysis
    // ============================================
    async analyzeSentiment(text) {
        const prompt = `Analyze the sentiment and emotion of this message. Return ONLY a JSON object with: sentiment (positive/negative/neutral/mixed), score (-1 to 1), emotion (happy/sad/angry/excited/anxious/neutral/urgent/grateful), confidence (0-1). Message: "${text}"`;
        
        const response = await this.quick(prompt, 'You are a sentiment analysis expert. Be precise.', {
            maxTokens: 150,
            temperature: 0.1
        });
        
        try {
            // Extract JSON from response
            const jsonMatch = response.match(/\{[\s\S]*\}/);
            if (jsonMatch) return JSON.parse(jsonMatch[0]);
            
            // Fallback
            return { sentiment: 'neutral', score: 0, emotion: 'neutral', confidence: 0.5 };
        } catch {
            return { sentiment: 'neutral', score: 0, emotion: 'neutral', confidence: 0.5 };
        }
    }
    
    // ============================================
    // Topic Extraction
    // ============================================
    async extractTopics(text, maxTopics = 5) {
        const prompt = `Extract up to ${maxTopics} key topics from this message. Return ONLY a JSON array of strings. Message: "${text}"`;
        
        const response = await this.quick(prompt, 'You extract concise topics from text.', { maxTokens: 100 });
        
        try {
            const jsonMatch = response.match(/\[[\s\S]*\]/);
            if (jsonMatch) return JSON.parse(jsonMatch[0]);
            return [];
        } catch {
            return [];
        }
    }
    
    // ============================================
    // Intent Classification
    // ============================================
    async classifyIntent(text) {
        const prompt = `Classify the intent of this WhatsApp message. Return ONLY a JSON object with: intent (greeting/question/request/complaint/urgent/business/personal/other), urgency (low/medium/high/critical), needs_human (boolean). Message: "${text}"`;
        
        const response = await this.quick(prompt, null, { maxTokens: 100 });
        
        try {
            const jsonMatch = response.match(/\{[\s\S]*\}/);
            if (jsonMatch) return JSON.parse(jsonMatch[0]);
            return { intent: 'other', urgency: 'low', needs_human: false };
        } catch {
            return { intent: 'other', urgency: 'low', needs_human: false };
        }
    }
    
    // ============================================
    // Helpers
    // ============================================
    calculateCost(model, inputTokens, outputTokens) {
        const config = MODELS[model] || MODELS[DEFAULT_MODEL];
        const inputCost = (inputTokens / 1_000_000) * config.input;
        const outputCost = (outputTokens / 1_000_000) * config.output;
        return parseFloat((inputCost + outputCost).toFixed(6));
    }
    
    getFallbackResponse(type) {
        const fallbacks = {
            negotiation: 'Let me check and get back to you on that.',
            greeting: 'Hey! How far?',
            business: 'I\'ll review this and get back to you shortly.',
            casual: 'Ah I see. Talk soon!',
            emotional: 'I\'m here. Tell me what\'s going on.',
            default: 'Let me get back to you on this.'
        };
        return fallbacks[type] || fallbacks.default;
    }
    
    getStats() {
        return {
            requests: this.requestCount,
            errors: this.errorCount,
            totalCost: this.totalCost.toFixed(4),
            isHealthy: this.isHealthy,
            lastError: this.lastError
        };
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

module.exports = new AIClient();
