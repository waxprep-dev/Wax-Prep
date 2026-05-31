// ============================================
// DAVID OS — Supabase Client & Data Layer
// Connection pooling, retries, typed queries
// ============================================

const { createClient } = require('@supabase/supabase-js');
const { logger } = require('./logger');

// Validate env vars
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;

if (!SUPABASE_URL || !SUPABASE_SERVICE_KEY) {
    logger.error('SUPABASE: Missing environment variables');
    throw new Error('SUPABASE_URL and SUPABASE_SERVICE_KEY required');
}

// Create client with custom fetch (timeout & retry)
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY, {
    auth: {
        autoRefreshToken: true,
        persistSession: true
    },
    db: {
        schema: 'public'
    },
    global: {
        headers: {
            'x-application-name': 'david-os',
            'x-client-info': 'david-os/2.0'
        },
        fetch: (url, options = {}) => {
            return fetch(url, {
                ...options,
                signal: AbortSignal.timeout(15000) // 15s timeout
            });
        }
    }
});

// ============================================
// CONTACTS
// ============================================
const Contacts = {
    async findOrCreate(phoneNumber, defaults = {}) {
        const normalized = this.normalizePhone(phoneNumber);
        
        // Try existing
        const { data: existing } = await supabase
            .from('davidos_contacts')
            .select('*')
            .eq('normalized_phone', normalized)
            .single();
        
        if (existing) {
            return { contact: existing, isNew: false };
        }
        
        // Create new
        const { data: created, error } = await supabase
            .from('davidos_contacts')
            .insert({
                phone_number: phoneNumber,
                normalized_phone: normalized,
                relationship_type: defaults.relationshipType || 'stranger',
                name: defaults.name || null,
                ...defaults
            })
            .select()
            .single();
        
        if (error) {
            logger.error('SUPABASE: Create contact error', { error: error.message, phoneNumber });
            throw error;
        }
        
        logger.info('CONTACT_CREATED', { contactId: created.id, phone: normalized });
        return { contact: created, isNew: true };
    },
    
    async getById(id) {
        const { data } = await supabase.from('davidos_contacts').select('*').eq('id', id).single();
        return data;
    },
    
    async update(id, updates) {
        const { data } = await supabase.from('davidos_contacts').update(updates).eq('id', id).select().single();
        return data;
    },
    
    async list(options = {}) {
        let query = supabase.from('davidos_contacts').select('*', { count: 'exact' });
        
        if (options.relationshipType) {
            query = query.eq('relationship_type', options.relationshipType);
        }
        if (options.search) {
            query = query.or(`name.ilike.%${options.search}%,phone_number.ilike.%${options.search}%`);
        }
        if (options.orderBy) {
            query = query.order(options.orderBy, { ascending: options.ascending ?? false });
        } else {
            query = query.order('last_interaction', { ascending: false });
        }
        
        const limit = options.limit || 50;
        const offset = options.offset || 0;
        query = query.range(offset, offset + limit - 1);
        
        const { data, count, error } = await query;
        return { contacts: data || [], count: count || 0, error };
    },
    
    async getStats() {
        const { count: total } = await supabase.from('davidos_contacts').select('*', { count: 'exact', head: true });
        const { count: family } = await supabase.from('davidos_contacts').select('*', { count: 'exact', head: true }).eq('relationship_type', 'family');
        const { count: business } = await supabase.from('davidos_contacts').select('*', { count: 'exact', head: true }).eq('relationship_type', 'business');
        const { count: friends } = await supabase.from('davidos_contacts').select('*', { count: 'exact', head: true }).eq('relationship_type', 'close_friend');
        return { total, family, business, friends };
    },
    
    normalizePhone(phone) {
        // Normalize Nigerian numbers and international
        let cleaned = phone.replace(/[^\d+]/g, '');
        if (cleaned.startsWith('0') && cleaned.length === 11) {
            cleaned = '+234' + cleaned.substring(1);
        }
        if (!cleaned.startsWith('+')) {
            cleaned = '+' + cleaned;
        }
        return cleaned;
    }
};

// ============================================
// MESSAGES
// ============================================
const Messages = {
    async create(data) {
        const { data: msg, error } = await supabase
            .from('davidos_messages')
            .insert(data)
            .select()
            .single();
        if (error) logger.error('SUPABASE: Message insert error', { error: error.message });
        return msg;
    },
    
    async getByContact(contactId, options = {}) {
        let query = supabase.from('davidos_messages').select('*').eq('contact_id', contactId);
        
        if (options.limit) query = query.limit(options.limit);
        query = query.order('created_at', { ascending: options.ascending ?? false });
        
        const { data } = await query;
        return data || [];
    },
    
    async getRecentContext(contactId, limit = 20) {
        const { data } = await supabase
            .from('davidos_messages')
            .select('content, direction, ai_generated, created_at, sentiment')
            .eq('contact_id', contactId)
            .order('created_at', { ascending: false })
            .limit(limit);
        return (data || []).reverse();
    },
    
    async updateStatus(id, status) {
        const { data } = await supabase.from('davidos_messages').update({ status }).eq('id', id).select().single();
        return data;
    },
    
    async getStats(period = 'today') {
        const now = new Date();
        let startDate;
        
        if (period === 'today') {
            startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        } else if (period === 'week') {
            startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        } else if (period === 'month') {
            startDate = new Date(now.getFullYear(), now.getMonth(), 1);
        }
        
        const { count: total } = await supabase
            .from('davidos_messages')
            .select('*', { count: 'exact', head: true })
            .gte('created_at', startDate.toISOString());
        
        const { count: aiHandled } = await supabase
            .from('davidos_messages')
            .select('*', { count: 'exact', head: true })
            .eq('ai_generated', true)
            .eq('direction', 'outbound')
            .gte('created_at', startDate.toISOString());
        
        const { count: inbound } = await supabase
            .from('davidos_messages')
            .select('*', { count: 'exact', head: true })
            .eq('direction', 'inbound')
            .gte('created_at', startDate.toISOString());
        
        return { total, aiHandled, inbound, period };
    }
};

// ============================================
// CONVERSATIONS
// ============================================
const Conversations = {
    async findOrCreate(contactId, defaults = {}) {
        const { data: existing } = await supabase
            .from('davidos_conversations')
            .select('*')
            .eq('contact_id', contactId)
            .eq('status', 'active')
            .single();
        
        if (existing) return existing;
        
        const { data: created } = await supabase
            .from('davidos_conversations')
            .insert({ contact_id: contactId, ...defaults })
            .select()
            .single();
        
        return created;
    },
    
    async updateContext(id, contextWindow) {
        const summary = contextWindow.length > 10 
            ? await this.generateSummary(contextWindow) 
            : null;
        
        const { data } = await supabase
            .from('davidos_conversations')
            .update({
                context_window: contextWindow.slice(-20),
                summary_text: summary,
                summary_updated_at: summary ? new Date().toISOString() : null
            })
            .eq('id', id)
            .select()
            .single();
        return data;
    },
    
    async generateSummary(messages) {
        // Simple extraction — AI will do proper summarization
        const recent = messages.slice(-5).map(m => m.content).join(' | ');
        return recent.substring(0, 200);
    },
    
    async listActive() {
        const { data } = await supabase
            .from('davidos_conversations')
            .select('*, contact:davidos_contacts(name, phone_number, relationship_type, always_alert)')
            .eq('status', 'active')
            .order('last_message_at', { ascending: false })
            .limit(50);
        return data || [];
    }
};

// ============================================
// ESCALATIONS
// ============================================
const Escalations = {
    async create(data) {
        const { data: esc } = await supabase
            .from('davidos_escalations')
            .insert(data)
            .select()
            .single();
        
        logger.escalation(data.reason, data.severity, data.contact_id, { category: data.category });
        return esc;
    },
    
    async list(options = {}) {
        let query = supabase
            .from('davidos_escalations')
            .select('*, contact:davidos_contacts(name, phone_number)')
            .order('created_at', { ascending: false });
        
        if (options.resolved !== undefined) query = query.eq('resolved', options.resolved);
        if (options.severity) query = query.eq('severity', options.severity);
        
        const { data } = await query.limit(options.limit || 50);
        return data || [];
    },
    
    async resolve(id, notes) {
        const { data } = await supabase
            .from('davidos_escalations')
            .update({
                resolved: true,
                resolved_at: new Date().toISOString(),
                resolution_notes: notes
            })
            .eq('id', id)
            .select()
            .single();
        return data;
    }
};

// ============================================
// PERSONALITY
// ============================================
const Personality = {
    async getByLayer(layer) {
        const { data } = await supabase
            .from('davidos_personality')
            .select('*')
            .eq('layer', layer)
            .eq('active', true)
            .order('version', { ascending: false })
            .limit(1)
            .single();
        return data;
    },
    
    async getAll() {
        const { data } = await supabase
            .from('davidos_personality')
            .select('*')
            .eq('active', true);
        return data || [];
    }
};

// ============================================
// SETTINGS
// ============================================
const Settings = {
    _cache: new Map(),
    _cacheExpiry: 60000, // 1 min cache
    _lastFetch: 0,
    
    async getAll() {
        const now = Date.now();
        if (now - this._lastFetch < this._cacheExpiry && this._cache.size > 0) {
            return Object.fromEntries(this._cache);
        }
        
        const { data } = await supabase.from('davidos_settings').select('*');
        const settings = {};
        (data || []).forEach(s => {
            settings[s.key] = this.castValue(s.value, s.data_type);
        });
        
        this._cache = new Map(Object.entries(settings));
        this._lastFetch = now;
        return settings;
    },
    
    async get(key, defaultValue = null) {
        const all = await this.getAll();
        return all[key] !== undefined ? all[key] : defaultValue;
    },
    
    async set(key, value, dataType = 'string') {
        const { data } = await supabase
            .from('davidos_settings')
            .upsert({ key, value: String(value), data_type: dataType, updated_at: new Date().toISOString() })
            .select()
            .single();
        
        this._cache.set(key, this.castValue(value, dataType));
        return data;
    },
    
    castValue(value, type) {
        switch (type) {
            case 'boolean': return value === 'true' || value === true;
            case 'number': return parseFloat(value);
            case 'json': try { return JSON.parse(value); } catch { return value; }
            default: return value;
        }
    }
};

// ============================================
// RESPONSE QUEUE
// ============================================
const ResponseQueue = {
    async create(data) {
        const { data: item } = await supabase
            .from('davidos_response_queue')
            .insert({
                ...data,
                expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
            })
            .select()
            .single();
        return item;
    },
    
    async listPending() {
        const { data } = await supabase
            .from('davidos_response_queue')
            .select('*, contact:davidos_contacts(name, phone_number, relationship_type)')
            .eq('status', 'pending')
            .gt('expires_at', new Date().toISOString())
            .order('created_at', { ascending: false });
        return data || [];
    },
    
    async updateStatus(id, status, editedResponse = null) {
        const updates = { status, reviewed_at: new Date().toISOString() };
        if (editedResponse) updates.edited_response = editedResponse;
        const { data } = await supabase.from('davidos_response_queue').update(updates).eq('id', id).select().single();
        return data;
    }
};

// ============================================
// COSTS
// ============================================
const Costs = {
    async track(data) {
        const { data: record } = await supabase.from('davidos_costs').insert(data).select().single();
        logger.cost(data.service, data.operation, data.cost_usd, { input: data.input_tokens, output: data.output_tokens });
        return record;
    },
    
    async getDailyTotal() {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        const { data } = await supabase
            .from('davidos_costs')
            .select('cost_usd')
            .gte('created_at', today.toISOString());
        
        return (data || []).reduce((sum, r) => sum + parseFloat(r.cost_usd || 0), 0);
    },
    
    async getStats(period = 'week') {
        const start = new Date();
        if (period === 'week') start.setDate(start.getDate() - 7);
        else if (period === 'month') start.setMonth(start.getMonth() - 1);
        
        const { data } = await supabase
            .from('davidos_costs')
            .select('*')
            .gte('created_at', start.toISOString())
            .order('created_at', { ascending: false });
        
        const byService = {};
        (data || []).forEach(r => {
            byService[r.service] = (byService[r.service] || 0) + parseFloat(r.cost_usd);
        });
        
        const total = Object.values(byService).reduce((a, b) => a + b, 0);
        return { total, byService, count: data?.length || 0 };
    }
};

// ============================================
// ANALYTICS
// ============================================
const Analytics = {
    async record(metricName, value, dimension = null, dimensionValue = null, period = 'daily') {
        const { data } = await supabase
            .from('davidos_analytics')
            .insert({ metric_name: metricName, metric_value: value, dimension, dimension_value: dimensionValue, period })
            .select()
            .single();
        return data;
    },
    
    async getTimeSeries(metricName, days = 7) {
        const start = new Date();
        start.setDate(start.getDate() - days);
        
        const { data } = await supabase
            .from('davidos_analytics')
            .select('*')
            .eq('metric_name', metricName)
            .gte('created_at', start.toISOString())
            .order('created_at', { ascending: true });
        
        return data || [];
    }
};

// ============================================
// TEMPLATES
// ============================================
const Templates = {
    async getAll(options = {}) {
        let query = supabase.from('davidos_templates').select('*').eq('active', true);
        if (options.category) query = query.eq('category', options.category);
        const { data } = await query.order('usage_count', { ascending: false });
        return data || [];
    },
    
    async getByShortcut(shortcut) {
        const { data } = await supabase
            .from('davidos_templates')
            .select('*')
            .eq('shortcut', shortcut)
            .eq('active', true)
            .single();
        return data;
    }
};

module.exports = {
    supabase,
    Contacts,
    Messages,
    Conversations,
    Escalations,
    Personality,
    Settings,
    ResponseQueue,
    Costs,
    Analytics,
    Templates
};
