-- ==============================================================================
-- Migration: Create support_escalations Table for Level 5 Human Support Escalations
-- Version: 20260910120000
-- ==============================================================================

CREATE TABLE IF NOT EXISTS support_escalations (
    ticket_id VARCHAR(32) PRIMARY KEY,
    customer_unique_id VARCHAR(32) NOT NULL,
    demo_customer_id VARCHAR(32),
    reason TEXT NOT NULL,
    conversation_summary TEXT,
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Optimize lookups by customer and status
CREATE INDEX IF NOT EXISTS idx_support_escalations_customer_unique_id 
    ON support_escalations(customer_unique_id);

CREATE INDEX IF NOT EXISTS idx_support_escalations_status 
    ON support_escalations(status);
