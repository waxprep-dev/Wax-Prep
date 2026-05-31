#!/usr/bin/env node
// ============================================
// DAVID OS — Daily Digest
// Sends summary of yesterday's activity
// Run via cron: 0 8 * * * node scripts/daily-digest.js
// ============================================

require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_SERVICE_KEY
);

async function generateDigest() {
    console.log('[DIGEST] Generating daily digest...');
    
    try {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        yesterday.setHours(0, 0, 0, 0);
        
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        
        // Message stats
        const { count: totalMessages } = await supabase
            .from('davidos_messages')
            .select('*', { count: 'exact', head: true })
            .gte('created_at', yesterday.toISOString())
            .lt('created_at', today.toISOString());
        
        const { count: aiHandled } = await supabase
            .from('davidos_messages')
            .select('*', { count: 'exact', head: true })
            .eq('ai_generated', true)
            .eq('direction', 'outbound')
            .gte('created_at', yesterday.toISOString())
            .lt('created_at', today.toISOString());
        
        // Escalations
        const { data: escalations } = await supabase
            .from('davidos_escalations')
            .select('*')
            .gte('created_at', yesterday.toISOString())
            .lt('created_at', today.toISOString());
        
        // Top contacts
        const { data: topContacts } = await supabase
            .from('davidos_messages')
            .select('phone_number, contact:davidos_contacts(name)')
            .gte('created_at', yesterday.toISOString())
            .lt('created_at', today.toISOString())
            .eq('direction', 'inbound');
        
        const contactCounts = {};
        (topContacts || []).forEach(m => {
            const key = m.contact?.name || m.phone_number;
            contactCounts[key] = (contactCounts[key] || 0) + 1;
        });
        
        const sortedContacts = Object.entries(contactCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5);
        
        // Cost
        const { data: costs } = await supabase
            .from('davidos_costs')
            .select('cost_usd')
            .gte('created_at', yesterday.toISOString())
            .lt('created_at', today.toISOString());
        
        const totalCost = (costs || []).reduce((s, c) => s + parseFloat(c.cost_usd || 0), 0);
        
        const digest = {
            date: yesterday.toDateString(),
            messages: { total: totalMessages, aiHandled },
            escalations: escalations?.length || 0,
            topContacts: sortedContacts,
            cost: totalCost.toFixed(4)
        };
        
        console.log('[DIGEST]', JSON.stringify(digest, null, 2));
        
        // Store digest
        await supabase.from('davidos_analytics').insert({
            metric_name: 'daily_digest',
            metric_value: 1,
            dimension: 'digest',
            dimension_value: JSON.stringify(digest),
            period: 'daily'
        });
        
        console.log('[DIGEST] Done ✓');
        process.exit(0);
    } catch (error) {
        console.error('[DIGEST ERROR]', error.message);
        process.exit(1);
    }
}

generateDigest();
