#!/usr/bin/env node
// ============================================
// DAVID OS — Daily Cleanup Script
// Archives old conversations, cleans logs
// Run via cron: 0 2 * * * node scripts/cleanup.js
// ============================================

require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');

const supabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_SERVICE_KEY
);

async function cleanup() {
    console.log('[CLEANUP] Starting daily cleanup...');
    
    try {
        // Archive conversations older than 90 days
        const archiveDate = new Date();
        archiveDate.setDate(archiveDate.getDate() - 90);
        
        const { data: archived } = await supabase
            .from('davidos_conversations')
            .update({ status: 'archived' })
            .lt('last_message_at', archiveDate.toISOString())
            .eq('status', 'active');
        
        console.log(`[CLEANUP] Archived ${archived?.length || 0} old conversations`);
        
        // Clean old analytics
        const analyticsDate = new Date();
        analyticsDate.setDate(analyticsDate.getDate() - 30);
        
        await supabase
            .from('davidos_analytics')
            .delete()
            .lt('created_at', analyticsDate.toISOString());
        
        console.log('[CLEANUP] Cleaned old analytics');
        
        // Clean old audit logs (keep 90 days)
        const auditDate = new Date();
        auditDate.setDate(auditDate.getDate() - 90);
        
        await supabase
            .from('davidos_audit_log')
            .delete()
            .lt('created_at', auditDate.toISOString());
        
        console.log('[CLEANUP] Cleaned old audit logs');
        
        console.log('[CLEANUP] Done ✓');
        process.exit(0);
    } catch (error) {
        console.error('[CLEANUP ERROR]', error.message);
        process.exit(1);
    }
}

cleanup();
