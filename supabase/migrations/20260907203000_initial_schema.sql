-- ==============================================================================
-- Initial Database Schema Migration for Capstone Project
-- "Autonomous AI Customer Support & Resolution Agent"
-- Migration Version: 20260907203000
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Product Category Translation Table
CREATE TABLE IF NOT EXISTS product_category_name_translation (
    product_category_name VARCHAR(100) PRIMARY KEY,
    product_category_name_english VARCHAR(100) NOT NULL
);

-- 3. Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(32) PRIMARY KEY,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix VARCHAR(10),
    customer_city VARCHAR(100),
    customer_state VARCHAR(10)
);

-- 4. Products Table (retains both Portuguese category and English translation)
CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(32) PRIMARY KEY,
    product_category_name VARCHAR(100) REFERENCES product_category_name_translation(product_category_name) ON DELETE SET NULL,
    product_category_name_english VARCHAR(100),
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g NUMERIC(10, 2),
    product_length_cm NUMERIC(10, 2),
    product_height_cm NUMERIC(10, 2),
    product_width_cm NUMERIC(10, 2)
);

-- 5. Orders Table
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(32) PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL REFERENCES customers(customer_id) ON DELETE RESTRICT,
    customer_unique_id VARCHAR(32) NOT NULL,
    order_status VARCHAR(50) NOT NULL,
    order_purchase_timestamp TIMESTAMPTZ NOT NULL,
    order_approved_at TIMESTAMPTZ,
    order_delivered_carrier_date TIMESTAMPTZ,
    order_delivered_customer_date TIMESTAMPTZ,
    order_estimated_delivery_date TIMESTAMPTZ NOT NULL
);

-- 6. Order Items Table (Composite PK: order_id, order_item_id)
CREATE TABLE IF NOT EXISTS order_items (
    order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    order_item_id INTEGER NOT NULL,
    product_id VARCHAR(32) NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    seller_id VARCHAR(32) NOT NULL,
    shipping_limit_date TIMESTAMPTZ NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    freight_value NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);

-- 7. Order Payments Table (Composite PK: order_id, payment_sequential)
CREATE TABLE IF NOT EXISTS order_payments (
    order_id VARCHAR(32) NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    payment_sequential INTEGER NOT NULL,
    payment_type VARCHAR(50) NOT NULL,
    payment_installments INTEGER NOT NULL,
    payment_value NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential)
);

-- 8. Customer Support Intents Table (Bitext)
CREATE TABLE IF NOT EXISTS customer_support_intents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    flags VARCHAR(20) NOT NULL,
    instruction TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    intent VARCHAR(50) NOT NULL,
    response TEXT NOT NULL
);

-- 9. Customer Demo Accounts Table (Deterministic Synthetic Personas)
CREATE TABLE IF NOT EXISTS customer_demo_accounts (
    demo_customer_id VARCHAR(20) PRIMARY KEY,
    customer_unique_id VARCHAR(32) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    demo_email VARCHAR(150) NOT NULL UNIQUE,
    total_orders INTEGER NOT NULL,
    primary_scenario VARCHAR(100) NOT NULL,
    sample_order_id VARCHAR(32) REFERENCES orders(order_id) ON DELETE SET NULL,
    customer_city VARCHAR(100),
    customer_state VARCHAR(10)
);

-- ==============================================================================
-- Targeted Query Indexes for AI Agent and Customer Support Lookup Performance
-- ==============================================================================

-- Customers lookups
CREATE INDEX IF NOT EXISTS idx_customers_unique_id ON customers(customer_unique_id);

-- Orders lookups
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer_unique_id ON orders(customer_unique_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer_status_date ON orders(customer_unique_id, order_status, order_purchase_timestamp DESC);

-- Order items lookups
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

-- Order payments lookups
CREATE INDEX IF NOT EXISTS idx_order_payments_order_id ON order_payments(order_id);

-- Products lookups
CREATE INDEX IF NOT EXISTS idx_products_category ON products(product_category_name);
CREATE INDEX IF NOT EXISTS idx_products_category_english ON products(product_category_name_english);

-- Customer support intents lookups
CREATE INDEX IF NOT EXISTS idx_cs_intents_category_intent ON customer_support_intents(category, intent);

-- Demo accounts lookups
CREATE INDEX IF NOT EXISTS idx_demo_customer_unique_id ON customer_demo_accounts(customer_unique_id);
