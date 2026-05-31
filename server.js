#!/usr/bin/env node
// ============================================
// DAVID OS v2.0 — Personal AI Digital Twin
// WhatsApp AI Clone with Personality Engine
// ============================================

require('dotenv').config();

const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const cron = require('node-cron');
const path = require('path');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const qrcodeTerminal = require('qrcode-terminal');
const WebSocket = require('ws');

// Utils
const { logger } = require('./src/utils/logger');
const { supabase, Contacts, Messages, Conversations, Escalations, Settings, ResponseQueue, Costs, Analytics, Templates } = require('./src/utils/supabase');
const ai = require('./src/utils/groq');

// Brain
const personality = require('./src/brain/personality');
const memory = require('./src/brain/memory');
const silence = require('./src/brain/silence');
const escalation = require('./src/brain/escalation');

// ============================================
// CONFIGURATION
// ============================================
const PORT = process.env.PORT || 3000;
const HOST = process.env.HOST || '0.0.0.0';

// ============================================
// EXPRESS APP
// ============================================
const app = express();
app.use(helmet({
    contentSecurityPolicy: {
        directives: {
            defaultSrc: ["'self'"],
            scriptSrc: ["'self'", "'unsafe-inline'", "'unsafe-eval'", "cdn.jsdelivr.net", "unpkg.com"],
            styleSrc: ["'self'", "'unsafe-inline'", "fonts.googleapis.com", "cdn.jsdelivr.net"],
            fontSrc: ["'self'", "fonts.gstatic.com"],
            imgSrc: ["'self'", "data:", "blob:"],
            connectSrc: ["'self'", "*.supabase.co"]
        }
    }
}));
app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// Rate limiting
const apiLimiter = rateLimit({
    windowMs: 60 * 1000,
    max: 100,
    message: { error: 'Too many requests. Slow down bro.' }
});
app.use('/api/', apiLimiter);

// ============================================
// STATE MANAGEMENT
// ============================================
const state = {
    aiEnabled: true,
    whatsappReady: false,
    qrCode: null,
    startTime: Date.now(),
    stats: {
        messagesReceived: 0,
        messagesSent: 0,
        aiHandled: 0,
        escalated: 0,
        errors: 0
    },
    connectedClients: new Set()
};

// ============================================
// WHATSAPP CLIENT
// ============================================
const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: process.env.WA_SESSION_NAME || 'david-os-session'
    }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu',
            '--disable-web-security'
        ],
        executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined
    },
    qrMaxRetries: 5,
    takeoverOnConflict: true,
    takeoverTimeoutMs: 5000
});

// QR Code Handler
client.on('qr', async (qr) => {
    logger.info('WHATSAPP_QR_READY');
    state.qrCode = qr;
    
    // Terminal QR
    qrcodeTerminal.generate(qr, { small: true });
    
    // Generate data URL for dashboard
    try {
        const qrDataUrl = await qrcode.toDataURL(qr, { width: 400, margin: 2 });
        state.qrDataUrl = qrDataUrl;
    } catch (err) {
        logger.error('QR_GENERATE_ERROR', { error: err.message });
    }
    
    broadcast({ type: 'qr', qr: state.qrDataUrl });
});

// Ready Handler
client.on('ready', () => {
    logger.info('WHATSAPP_READY');
    state.whatsappReady = true;
    state.qrCode = null;
    state.qrDataUrl = null;
    broadcast({ type: 'status', status: 'connected', message: 'WhatsApp connected!' });
});

// Auth Failure
client.on('auth_failure', (msg) => {
    logger.error('WHATSAPP_AUTH_FAILURE', { message: msg });
    state.whatsappReady = false;
    broadcast({ type: 'status', status: 'auth_failed', message: msg });
});

// Disconnected
client.on('disconnected', (reason) => {
    logger.warn('WHATSAPP_DISCONNECTED', { reason });
    state.whatsappReady = false;
    broadcast({ type: 'status', status: 'disconnected', message: reason });
    
    // Auto-reconnect after 5 seconds
    setTimeout(() => {
        logger.info('WHATSAPP_RECONNECTING');
        client.initialize().catch(err => {
            logger.error('WHATSAPP_RECONNECT_ERROR', { error: err.message });
        });
    }, 5000);
});

// ============================================
// MESSAGE HANDLER — THE CORE
// ============================================
client.on('message_create', async (msg) => {
    // Only handle inbound messages
    if (msg.fromMe) {
        // Track David's manual replies for learning
        await handleManualReply(msg);
        return;
    }
    
    // Ignore status broadcasts, groups (for now)
    if (msg.from === 'status@broadcast') return;
    if (msg.from.endsWith('@g.us')) {
        await handleGroupMessage(msg);
        return;
    }
    
    state.stats.messagesReceived++;
    
    const startTime = Date.now();
    
    try {
        // Step 1: Get or create contact
        const { contact: dbContact, isNew } = await Contacts.findOrCreate(msg.from, {
            name: msg.notifyName || msg._data.notifyName
        });
        
        // Step 2: Store incoming message
        const messageRecord = await Messages.create({
            contact_id: dbContact.id,
            phone_number: msg.from,
            direction: 'inbound',
            content: msg.body || '[media]',
            content_type: getContentType(msg.type),
            status: 'delivered'
        });
        
        // Step 3: Analyze sentiment & intent
        const [sentiment, intent] = await Promise.all([
            ai.analyzeSentiment(msg.body || ''),
            ai.classifyIntent(msg.body || '')
        ]);
        
        // Update message with analysis
        await supabase.from('davidos_messages').update({
            sentiment: sentiment.sentiment,
            sentiment_score: sentiment.score,
            emotion: sentiment.emotion,
            intent: intent.intent
        }).eq('id', messageRecord.id);
        
        // Step 4: Build conversation context
        const conversationContext = await memory.buildContext(dbContact.id);
        
        // Step 5: Silence check — should we reply?
        const silenceCheck = await silence.shouldReply(msg, dbContact, conversationContext.messages);
        
        if (!silenceCheck.shouldReply) {
            logger.info('SILENCE_ACTIVE', { 
                reason: silenceCheck.reason, 
                contactId: dbContact.id,
                preview: (msg.body || '').substring(0, 50)
            });
            
            // Still store but mark as not replied
            await supabase.from('davidos_messages').update({
                status: 'read',
                metadata: { silence_reason: silenceCheck.reason }
            }).eq('id', messageRecord.id);
            
            broadcast({
                type: 'message',
                direction: 'inbound',
                contact: dbContact,
                message: messageRecord,
                aiHandled: false,
                silenceReason: silenceCheck.reason
            });
            
            return;
        }
        
        // Step 6: Check escalation triggers
        const escalationCheck = await escalation.check(msg, dbContact, conversationContext.messages);
        
        if (escalationCheck.escalated && escalationCheck.immediate) {
            // Critical escalation — don't auto-reply
            logger.info('CRITICAL_ESCALATION', { 
                trigger: escalationCheck.primary.type,
                contactId: dbContact.id 
            });
            
            await Messages.updateStatus(messageRecord.id, 'escalated');
            
            broadcast({
                type: 'escalation',
                escalation: escalationCheck.escalation,
                contact: dbContact,
                message: messageRecord
            });
            
            return;
        }
        
        // Step 7: Check response queue setting
        const queueThreshold = await Settings.get('confidence_threshold', 0.7);
        
        // Step 8: Build personality context and get AI response
        const personalityContext = await personality.buildContext(dbContact, msg, conversationContext.messages);
        
        const aiResponse = await ai.chat(personalityContext.messages, {
            temperature: personalityContext.config.temperature,
            maxTokens: personalityContext.config.maxTokens,
            contactId: dbContact.id,
            messageId: messageRecord.id,
            operation: 'whatsapp_response'
        });
        
        // Step 9: Post-process response
        const processedResponse = personality.postProcessResponse(
            aiResponse, 
            personalityContext.personality, 
            personalityContext.signals
        );
        
        const confidence = aiResponse.fallback ? 0.3 : 0.85;
        
        // Step 10: Check if response needs approval (queue mode)
        if (confidence < queueThreshold && !dbContact.trust_level || dbContact.trust_level < 70) {
            // Add to response queue
            const queueItem = await ResponseQueue.create({
                contact_id: dbContact.id,
                message_id: messageRecord.id,
                incoming_message: msg.body || '',
                suggested_response: processedResponse,
                ai_confidence: confidence,
                context_summary: conversationContext.summary
            });
            
            logger.info('RESPONSE_QUEUED', { queueId: queueItem.id, confidence });
            
            broadcast({
                type: 'queue',
                item: queueItem,
                contact: dbContact
            });
            
            return;
        }
        
        // Step 11: Send response
        const responseTime = Date.now() - startTime;
        
        // Calculate typing delay
        const delay = silence.calculateDelay(dbContact, processedResponse, conversationContext.messages.length);
        
        // Simulate typing and send
        await sendWithDelay(msg.from, processedResponse, delay);
        
        // Step 12: Store outbound message
        const outboundRecord = await Messages.create({
            contact_id: dbContact.id,
            phone_number: msg.from,
            direction: 'outbound',
            content: processedResponse,
            ai_generated: true,
            confidence_score: confidence,
            status: 'sent',
            response_time_ms: responseTime
        });
        
        state.stats.messagesSent++;
        state.stats.aiHandled++;
        
        // Step 13: Update conversation
        await Conversations.updateContext(
            (await Conversations.findOrCreate(dbContact.id)).id,
            [...conversationContext.messages, {
                role: 'assistant',
                content: processedResponse
            }]
        );
        
        // Step 14: Track analytics
        Analytics.record('message_handled', 1, 'ai', 'true');
        Analytics.record('response_time', responseTime, 'contact', dbContact.relationship_type);
        
        // Broadcast update
        broadcast({
            type: 'message',
            direction: 'outbound',
            contact: dbContact,
            message: outboundRecord,
            aiHandled: true,
            responseTime,
            cost: aiResponse.cost
        });
        
        logger.info('MESSAGE_HANDLED', {
            contactId: dbContact.id,
            responseTime,
            cost: aiResponse.cost,
            confidence,
            layer: personalityContext.layer
        });
        
    } catch (error) {
        state.stats.errors++;
        logger.error('MESSAGE_HANDLER_ERROR', {
            error: error.message,
            stack: error.stack,
            from: msg.from,
            preview: (msg.body || '').substring(0, 100)
        });
    }
});

// ============================================
// MESSAGE SEND WITH DELAY (Human-like)
// ============================================
async function sendWithDelay(to, content, delayMs) {
    // Wait for typing delay
    if (delayMs > 0) {
        await new Promise(r => setTimeout(r, delayMs));
    }
    
    // Simulate typing indicator
    const chat = await client.getChatById(to);
    await chat.sendStateTyping();
    
    // Calculate typing duration based on message length
    const typingDuration = Math.min(content.length * 50, 3000); // 50ms per char, max 3s
    await new Promise(r => setTimeout(r, typingDuration));
    
    // Stop typing and send
    await chat.clearState();
    
    // Check if we should split into multiple messages
    const messages = silence.shouldSplitMessage(content);
    
    for (let i = 0; i < messages.length; i++) {
        await client.sendMessage(to, messages[i]);
        
        // Small gap between consecutive messages (like a real person)
        if (i < messages.length - 1) {
            await new Promise(r => setTimeout(r, 800 + Math.random() * 1200));
        }
    }
    
    return messages;
}

// ============================================
// HANDLE MANUAL REPLIES (David replies directly)
// ============================================
async function handleManualReply(msg) {
    try {
        // Find contact
        const to = msg.to;
        const { contact } = await Contacts.findOrCreate(to);
        
        // Store David's reply
        await Messages.create({
            contact_id: contact.id,
            phone_number: to,
            direction: 'outbound',
            content: msg.body || '',
            ai_generated: false,
            status: 'sent'
        });
        
        // This is a good learning signal — update trust
        if (contact.trust_level < 100) {
            await Contacts.update(contact.id, {
                trust_level: Math.min(100, contact.trust_level + 1)
            });
        }
        
        // Invalidate memory cache
        memory.invalidate(contact.id);
        
        logger.info('MANUAL_REPLY_DETECTED', { contactId: contact.id });
        
    } catch (error) {
        logger.error('MANUAL_REPLY_ERROR', { error: error.message });
    }
}

// ============================================
// GROUP MESSAGES
// ============================================
async function handleGroupMessage(msg) {
    // For now, just log group messages
    // Future: Mention detection, group-specific personality
    logger.info('GROUP_MESSAGE', {
        group: msg.from,
        author: msg.author,
        preview: (msg.body || '').substring(0, 50)
    });
}

// ============================================
// CONTENT TYPE DETECTION
// ============================================
function getContentType(type) {
    const typeMap = {
        'chat': 'text',
        'image': 'image',
        'video': 'video',
        'audio': 'voice',
        'ptt': 'voice', // Push to talk (voice note)
        'document': 'document',
        'sticker': 'sticker',
        'location': 'location',
        'vcard': 'contact',
        'multi_vcard': 'contact'
    };
    return typeMap[type] || 'text';
}

// ============================================
// WEBSOCKET SERVER (Real-time updates)
// ============================================
let wss;
function setupWebSocket(server) {
    wss = new WebSocket.Server({ server, path: '/ws' });
    
    wss.on('connection', (ws, req) => {
        logger.info('WS_CLIENT_CONNECTED', { ip: req.socket.remoteAddress });
        state.connectedClients.add(ws);
        
        // Send initial state
        ws.send(JSON.stringify({
            type: 'init',
            state: {
                aiEnabled: state.aiEnabled,
                whatsappReady: state.whatsappReady,
                hasQr: !!state.qrDataUrl,
                stats: state.stats
            }
        }));
        
        ws.on('close', () => {
            state.connectedClients.delete(ws);
        });
        
        ws.on('error', (err) => {
            logger.error('WS_ERROR', { error: err.message });
            state.connectedClients.delete(ws);
        });
    });
}

function broadcast(data) {
    const msg = JSON.stringify(data);
    state.connectedClients.forEach(ws => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(msg);
        }
    });
}

// ============================================
// API ROUTES
// ============================================

// Health Check
app.get('/health', (req, res) => {
    const uptime = Date.now() - state.startTime;
    res.json({
        status: 'healthy',
        version: '2.0.0',
        uptime: Math.floor(uptime / 1000),
        whatsapp: state.whatsappReady ? 'connected' : 'disconnected',
        aiEnabled: state.aiEnabled,
        stats: state.stats,
        aiStats: ai.getStats(),
        timestamp: new Date().toISOString()
    });
});

// QR Code Endpoint
app.get('/api/qr', (req, res) => {
    if (state.qrDataUrl) {
        res.json({ hasQr: true, qr: state.qrDataUrl });
    } else if (state.whatsappReady) {
        res.json({ hasQr: false, status: 'connected' });
    } else {
        res.json({ hasQr: false, status: 'waiting', message: 'QR code will appear when ready' });
    }
});

// Status Endpoint
app.get('/api/status', (req, res) => {
    res.json({
        whatsapp: state.whatsappReady ? 'connected' : state.qrCode ? 'waiting_for_scan' : 'initializing',
        aiEnabled: state.aiEnabled,
        uptime: Date.now() - state.startTime,
        stats: state.stats,
        ai: ai.getStats()
    });
});

// Toggle AI
app.post('/api/toggle-ai', async (req, res) => {
    state.aiEnabled = !state.aiEnabled;
    await Settings.set('ai_enabled', state.aiEnabled, 'boolean');
    broadcast({ type: 'settings', aiEnabled: state.aiEnabled });
    res.json({ aiEnabled: state.aiEnabled });
});

// ============================================
// CONTACTS API
// ============================================
app.get('/api/contacts', async (req, res) => {
    try {
        const { contacts, count, error } = await Contacts.list({
            search: req.query.search,
            relationshipType: req.query.type,
            limit: parseInt(req.query.limit) || 50,
            offset: parseInt(req.query.offset) || 0,
            orderBy: req.query.orderBy || 'last_interaction'
        });
        
        if (error) throw error;
        
        // Get stats for each contact
        const contactsWithStats = await Promise.all(contacts.map(async (c) => {
            const insights = await memory.getInsights(c.id);
            return { ...c, insights };
        }));
        
        res.json({ contacts: contactsWithStats, count });
    } catch (error) {
        logger.error('API_CONTACTS_ERROR', { error: error.message });
        res.status(500).json({ error: error.message });
    }
});

app.get('/api/contacts/:id', async (req, res) => {
    try {
        const contact = await Contacts.getById(req.params.id);
        if (!contact) return res.status(404).json({ error: 'Contact not found' });
        
        const messages = await Messages.getByContact(req.params.id, { limit: 50 });
        const insights = await memory.getInsights(req.params.id);
        
        res.json({ contact, messages, insights });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.patch('/api/contacts/:id', async (req, res) => {
    try {
        const contact = await Contacts.update(req.params.id, req.body);
        res.json(contact);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// MESSAGES API
// ============================================
app.get('/api/messages', async (req, res) => {
    try {
        const { contact_id, limit = 50 } = req.query;
        
        let query = supabase
            .from('davidos_messages')
            .select('*, contact:davidos_contacts(name, phone_number, relationship_type)')
            .order('created_at', { ascending: false })
            .limit(parseInt(limit));
        
        if (contact_id) query = query.eq('contact_id', contact_id);
        
        const { data, error } = await query;
        if (error) throw error;
        
        res.json({ messages: data || [] });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// CONVERSATIONS API
// ============================================
app.get('/api/conversations', async (req, res) => {
    try {
        const conversations = await Conversations.listActive();
        res.json({ conversations });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// ESCALATIONS API
// ============================================
app.get('/api/escalations', async (req, res) => {
    try {
        const escalations = await Escalations.list({
            resolved: req.query.resolved === 'true' ? true : req.query.resolved === 'false' ? false : undefined,
            limit: parseInt(req.query.limit) || 50
        });
        res.json({ escalations });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/escalations/:id/resolve', async (req, res) => {
    try {
        const escalation = await Escalations.resolve(req.params.id, req.body.notes);
        res.json(escalation);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// RESPONSE QUEUE API
// ============================================
app.get('/api/queue', async (req, res) => {
    try {
        const items = await ResponseQueue.listPending();
        res.json({ items });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/queue/:id/approve', async (req, res) => {
    try {
        const item = await ResponseQueue.updateStatus(req.params.id, 'approved');
        
        // Send the message
        if (item) {
            await sendWithDelay(
                (await Contacts.getById(item.contact_id)).phone_number,
                item.edited_response || item.suggested_response,
                2000
            );
        }
        
        res.json(item);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/queue/:id/reject', async (req, res) => {
    try {
        const item = await ResponseQueue.updateStatus(req.params.id, 'rejected');
        res.json(item);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.post('/api/queue/:id/edit', async (req, res) => {
    try {
        const item = await ResponseQueue.updateStatus(req.params.id, 'edited', req.body.response);
        
        // Send edited message
        if (item && req.body.response) {
            await sendWithDelay(
                (await Contacts.getById(item.contact_id)).phone_number,
                req.body.response,
                2000
            );
        }
        
        res.json(item);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// ANALYTICS API
// ============================================
app.get('/api/analytics', async (req, res) => {
    try {
        const { period = 'week' } = req.query;
        
        const [messageStats, costStats, escalationStats, contactStats] = await Promise.all([
            Messages.getStats('today'),
            Costs.getStats(period),
            escalation.getStats(),
            Contacts.getStats()
        ]);
        
        // Get hourly distribution
        const { data: hourlyData } = await supabase
            .from('davidos_messages')
            .select('created_at')
            .gte('created_at', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString());
        
        const hourlyDistribution = new Array(24).fill(0);
        (hourlyData || []).forEach(m => {
            const hour = new Date(m.created_at).getHours();
            hourlyDistribution[hour]++;
        });
        
        res.json({
            messages: messageStats,
            costs: costStats,
            escalations: escalationStats,
            contacts: contactStats,
            hourlyDistribution,
            aiStats: ai.getStats(),
            systemStats: state.stats
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// SETTINGS API
// ============================================
app.get('/api/settings', async (req, res) => {
    try {
        const settings = await Settings.getAll();
        res.json(settings);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.patch('/api/settings/:key', async (req, res) => {
    try {
        const setting = await Settings.set(req.params.key, req.body.value, req.body.type);
        
        // Update runtime state if needed
        if (req.params.key === 'ai_enabled') {
            state.aiEnabled = req.body.value === 'true' || req.body.value === true;
        }
        
        broadcast({ type: 'settings_update', key: req.params.key, value: req.body.value });
        res.json(setting);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// TEMPLATES API
// ============================================
app.get('/api/templates', async (req, res) => {
    try {
        const templates = await Templates.getAll({ category: req.query.category });
        res.json({ templates });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// VOICE NOTES API
// ============================================
app.get('/api/voice-notes', async (req, res) => {
    try {
        const { data, error } = await supabase
            .from('davidos_voice_notes')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(50);
        
        if (error) throw error;
        res.json({ voiceNotes: data || [] });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// SEND MESSAGE API (Manual override)
// ============================================
app.post('/api/send', async (req, res) => {
    try {
        const { phone, message } = req.body;
        
        if (!state.whatsappReady) {
            return res.status(400).json({ error: 'WhatsApp not connected' });
        }
        
        // Ensure proper format
        const formattedPhone = phone.includes('@c.us') ? phone : `${phone}@c.us`;
        
        await client.sendMessage(formattedPhone, message);
        
        // Store in database
        const { contact } = await Contacts.findOrCreate(phone);
        await Messages.create({
            contact_id: contact.id,
            phone_number: phone,
            direction: 'outbound',
            content: message,
            ai_generated: false,
            status: 'sent'
        });
        
        res.json({ sent: true });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// ============================================
// DASHBOARD
// ============================================
app.get('/dashboard', (req, res) => {
    res.sendFile(path.join(__dirname, 'dashboard.html'));
});

app.get('/', (req, res) => {
    res.redirect('/dashboard');
});

// ============================================
// ERROR HANDLING
// ============================================
app.use((err, req, res, next) => {
    logger.error('EXPRESS_ERROR', { error: err.message, path: req.path });
    res.status(500).json({ error: 'Internal server error' });
});

app.use((req, res) => {
    res.status(404).json({ error: 'Not found' });
});

// ============================================
// CRON JOBS
// ============================================

// Clean old messages (daily at 2 AM)
cron.schedule('0 2 * * *', async () => {
    logger.info('CRON_CLEANUP_START');
    try {
        const archiveDays = await Settings.get('auto_archive_days', 90);
        const cutoff = new Date();
        cutoff.setDate(cutoff.getDate() - archiveDays);
        
        // Archive old conversations
        const { data: archived } = await supabase
            .from('davidos_conversations')
            .update({ status: 'archived' })
            .lt('last_message_at', cutoff.toISOString())
            .eq('status', 'active');
        
        logger.info('CRON_CLEANUP_DONE', { archived: archived?.length || 0 });
    } catch (error) {
        logger.error('CRON_CLEANUP_ERROR', { error: error.message });
    }
});

// Daily cost check
cron.schedule('0 9 * * *', async () => {
    try {
        const dailyCost = await Costs.getDailyTotal();
        const limit = await Settings.get('cost_limit_daily_usd', 10);
        
        if (dailyCost > limit) {
            logger.warn('DAILY_COST_LIMIT_EXCEEDED', { cost: dailyCost, limit });
            // Could disable AI or send alert
        }
        
        logger.info('DAILY_COST_CHECK', { cost: dailyCost.toFixed(4), limit });
    } catch (error) {
        logger.error('DAILY_COST_CHECK_ERROR', { error: error.message });
    }
});

// Health check broadcast
cron.schedule('*/30 * * * * *', () => {
    broadcast({
        type: 'heartbeat',
        timestamp: Date.now(),
        stats: state.stats,
        ai: ai.getStats()
    });
});

// ============================================
// GRACEFUL SHUTDOWN
// ============================================
async function shutdown(signal) {
    logger.info(`SHUTDOWN_${signal}`);
    
    // Close WebSocket connections
    if (wss) {
        wss.clients.forEach(ws => ws.close());
    }
    
    // Destroy WhatsApp client
    try {
        await client.destroy();
    } catch (e) {
        // Ignore
    }
    
    process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('uncaughtException', (err) => {
    logger.error('UNCAUGHT_EXCEPTION', { error: err.message, stack: err.stack });
    shutdown('UNCAUGHT_EXCEPTION');
});
process.on('unhandledRejection', (reason, promise) => {
    logger.error('UNHANDLED_REJECTION', { reason });
});

// ============================================
// START SERVER
// ============================================
const server = app.listen(PORT, HOST, async () => {
    logger.info('DAVID_OS_STARTING', { port: PORT, host: HOST, version: '2.0.0' });
    
    // Setup WebSocket
    setupWebSocket(server);
    
    // Initialize WhatsApp
    try {
        await client.initialize();
        logger.info('WHATSAPP_CLIENT_INITIALIZED');
    } catch (error) {
        logger.error('WHATSAPP_INIT_ERROR', { error: error.message });
    }
    
    logger.info('DAVID_OS_READY', { 
        url: `http://${HOST}:${PORT}`,
        dashboard: `http://${HOST}:${PORT}/dashboard`,
        health: `http://${HOST}:${PORT}/health`
    });
});

module.exports = { app, client, state, broadcast };
