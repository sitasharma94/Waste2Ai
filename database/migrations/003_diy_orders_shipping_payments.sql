-- =====================================================================
-- WASTE2VALUE - MIGRATION 003: DIY order shipping + online payments
-- =====================================================================
--
-- Adds nullable columns to an EXISTING `waste2value_final`.diy_orders
-- table (run after 001 and 002). Fresh installs don't need this file:
-- waste2value_final_schema.sql already contains the same columns.
--
--   status timestamps   confirmed_at, shipped_at, delivered_at, closed_at
--   shipment (manual)   courier_name, tracking_number, tracking_url
--   online payment      payment_provider, provider_order_id, provider_payment_id, paid_at
--                       (+ UNIQUE keys so one Razorpay order/payment can never
--                        be attached to two internal orders)
--
-- Additive only: every new column is NULL for existing orders, nothing is
-- dropped, renamed, updated or deleted, and no other table is touched.
-- New status values ('pending_payment') and payment statuses ('awaiting_payment',
-- 'paid', 'failed', 'expired', 'refund_pending', ...) fit the existing
-- varchar(20) columns, so those columns are unchanged.
--
-- Safe to run more than once: it checks information_schema first.
--
-- Run:  mysql -u root -p < database/migrations/003_diy_orders_shipping_payments.sql
-- =====================================================================

USE `waste2value_final`;

SET @has_cols := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'diy_orders'
      AND COLUMN_NAME = 'provider_order_id'
);

SET @ddl := IF(@has_cols = 0,
    'ALTER TABLE `diy_orders`
       ADD COLUMN `confirmed_at` timestamp NULL DEFAULT NULL,
       ADD COLUMN `shipped_at` timestamp NULL DEFAULT NULL,
       ADD COLUMN `delivered_at` timestamp NULL DEFAULT NULL,
       ADD COLUMN `closed_at` timestamp NULL DEFAULT NULL,
       ADD COLUMN `courier_name` varchar(100) DEFAULT NULL,
       ADD COLUMN `tracking_number` varchar(100) DEFAULT NULL,
       ADD COLUMN `tracking_url` varchar(500) DEFAULT NULL,
       ADD COLUMN `payment_provider` varchar(20) DEFAULT NULL,
       ADD COLUMN `provider_order_id` varchar(64) DEFAULT NULL,
       ADD COLUMN `provider_payment_id` varchar(64) DEFAULT NULL,
       ADD COLUMN `paid_at` timestamp NULL DEFAULT NULL,
       ADD UNIQUE KEY `uq_diy_orders_provider_order_id` (`provider_order_id`),
       ADD UNIQUE KEY `uq_diy_orders_provider_payment_id` (`provider_payment_id`)',
    'DO 0');

PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
