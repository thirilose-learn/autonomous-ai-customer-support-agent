-- Migration: 20260910130000_add_contact_to_support_escalations.sql
-- Add contact_email and contact_phone to support_escalations table.
-- Minimal additive extension for customer contact collection before escalation.

ALTER TABLE support_escalations 
ADD COLUMN IF NOT EXISTS contact_email VARCHAR(255),
ADD COLUMN IF NOT EXISTS contact_phone VARCHAR(50);
