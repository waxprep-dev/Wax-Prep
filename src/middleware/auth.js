// ============================================
// DAVID OS — Dashboard Authentication
// Simple password protection for dashboard
// ============================================

const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { logger } = require('../utils/logger');

const JWT_SECRET = process.env.JWT_SECRET || 'david-os-secret-change-in-production';
const PASSWORD_HASH = process.env.DASHBOARD_PASSWORD_HASH;

// Simple auth middleware for dashboard
function dashboardAuth(req, res, next) {
    // In production, require password
    // For development/render, can be disabled
    if (process.env.NODE_ENV === 'development' && !PASSWORD_HASH) {
        return next();
    }

    // Check for auth token in cookie or header
    const token = req.cookies?.auth || req.headers['x-auth-token'];
    
    if (token) {
        try {
            jwt.verify(token, JWT_SECRET);
            return next();
        } catch (e) {
            // Invalid token, fall through
        }
    }

    // API endpoints return 401, dashboard redirects to login
    if (req.path.startsWith('/api/')) {
        return res.status(401).json({ error: 'Authentication required' });
    }

    // For dashboard page, allow (auth handled client-side or via basic auth)
    next();
}

// Login endpoint
async function login(req, res) {
    const { password } = req.body;
    
    if (!password) {
        return res.status(400).json({ error: 'Password required' });
    }

    if (!PASSWORD_HASH) {
        return res.status(500).json({ error: 'Password not configured' });
    }

    const valid = await bcrypt.compare(password, PASSWORD_HASH);
    
    if (!valid) {
        logger.warn('AUTH_FAILED', { ip: req.ip });
        return res.status(401).json({ error: 'Invalid password' });
    }

    const token = jwt.sign({ role: 'admin' }, JWT_SECRET, { expiresIn: '7d' });
    
    res.cookie('auth', token, { httpOnly: true, maxAge: 7 * 24 * 60 * 60 * 1000 });
    res.json({ success: true, token });
}

module.exports = { dashboardAuth, login, JWT_SECRET };
