// ============================================
// DAVID OS — Advanced Logging System
// Winston with daily rotation, structured logs
// ============================================

const winston = require('winston');
const DailyRotateFile = require('winston-daily-rotate-file');
const path = require('path');

const { combine, timestamp, json, errors, printf } = winston.format;

// Custom format for console (human readable)
const consoleFormat = printf(({ level, message, timestamp, ...metadata }) => {
    let msg = `${timestamp} [${level.toUpperCase()}]: ${message}`;
    if (Object.keys(metadata).length > 0) {
        msg += ` | ${JSON.stringify(metadata)}`;
    }
    return msg;
});

// Create logs directory
const logsDir = process.env.LOGS_DIR || path.join(process.cwd(), 'logs');

// Daily rotating file transport
const fileRotateTransport = new DailyRotateFile({
    filename: path.join(logsDir, 'david-os-%DATE%.log'),
    datePattern: 'YYYY-MM-DD',
    maxSize: '20m',
    maxFiles: '30d',
    format: combine(
        timestamp(),
        json()
    )
});

// Separate error log
const errorTransport = new DailyRotateFile({
    filename: path.join(logsDir, 'david-os-error-%DATE%.log'),
    datePattern: 'YYYY-MM-DD',
    maxSize: '20m',
    maxFiles: '30d',
    level: 'error',
    format: combine(
        timestamp(),
        json()
    )
});

// Audit log for all AI decisions
const auditTransport = new DailyRotateFile({
    filename: path.join(logsDir, 'david-os-audit-%DATE%.log'),
    datePattern: 'YYYY-MM-DD',
    maxSize: '20m',
    maxFiles: '90d',
    format: combine(
        timestamp(),
        json()
    )
});

const logger = winston.createLogger({
    level: process.env.LOG_LEVEL || 'info',
    defaultMeta: {
        service: 'david-os',
        environment: process.env.NODE_ENV || 'development',
        pid: process.pid
    },
    transports: [
        fileRotateTransport,
        errorTransport,
        new winston.transports.Console({
            format: combine(
                timestamp(),
                consoleFormat
            )
        })
    ],
    exceptionHandlers: [fileRotateTransport, errorTransport],
    rejectionHandlers: [fileRotateTransport, errorTransport]
});

// Specialized audit logger for AI decisions
const auditLogger = winston.createLogger({
    level: 'info',
    defaultMeta: { type: 'audit' },
    transports: [auditTransport]
});

// Helper methods
logger.aiDecision = (data) => {
    auditLogger.info('AI_DECISION', {
        ...data,
        timestamp: new Date().toISOString()
    });
};

logger.messageFlow = (contactId, direction, content, metadata = {}) => {
    logger.info('MESSAGE_FLOW', {
        contactId,
        direction,
        contentLength: content?.length,
        ...metadata
    });
};

logger.escalation = (reason, severity, contactId, details = {}) => {
    logger.warn('ESCALATION_TRIGGERED', {
        reason,
        severity,
        contactId,
        ...details,
        timestamp: new Date().toISOString()
    });
};

logger.cost = (service, operation, cost, tokens = {}) => {
    logger.info('COST_TRACKING', {
        service,
        operation,
        costUSD: cost,
        ...tokens
    });
};

module.exports = { logger, auditLogger };
