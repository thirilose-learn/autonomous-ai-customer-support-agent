# Relational Integrity Verification Report

### Foreign Key Validation Summary

- **`orders.customer_id` $\rightarrow$ `customers.customer_id`:**
  - Total orders: **99,441**
  - Unmatched customer foreign keys: **0 (0.00%)** - 100% Valid

- **`order_items.order_id` $\rightarrow$ `orders.order_id`:**
  - Total items: **112,650**
  - Unmatched order foreign keys: **0 (0.00%)** - 100% Valid

- **`order_items.product_id` $\rightarrow$ `products.product_id`:**
  - Total items: **112,650**
  - Unmatched product foreign keys: **0 (0.00%)** - 100% Valid

- **`order_payments.order_id` $\rightarrow$ `orders.order_id`:**
  - Total payments: **103,886**
  - Unmatched order foreign keys: **0 (0.00%)** - 100% Valid

### Null Values Semantic Justification

1. **`orders.order_delivered_customer_date` (2,965 NULLs):** Legitimately unfulfilled orders (statuses: canceled, unavailable, shipped, processing, invoiced, created, approved). Retained as NULL.
2. **`orders.order_delivered_carrier_date` (1,783 NULLs):** Orders not yet handed over to logistics. Retained as NULL.
3. **`orders.order_approved_at` (160 NULLs):** Canceled or pending-approval transactions. Retained as NULL.
4. **`products.product_category_name` (610 NULLs):** Unclassified catalog items. Standardized to empty string for database ingestion.
