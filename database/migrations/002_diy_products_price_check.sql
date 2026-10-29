-- =====================================================================
-- WASTE2VALUE - MIGRATION 002: no negative DIY product prices
-- =====================================================================
--
-- Adds   CONSTRAINT chk_diy_products_price CHECK (price >= 0)
-- to an EXISTING `waste2value_final`.diy_products table. Run after 001.
-- Fresh installs don't need this file: waste2value_final_schema.sql
-- already contains the constraint.
--
-- diy_products.price is already DECIMAL(10,2); its type is not changed.
--
-- Safe to run more than once: it checks information_schema first.
-- It never updates or deletes rows. If any existing product has a negative
-- price, MySQL refuses the ALTER with error 3819 ("Check constraint ... is
-- violated") and nothing changes. Find such rows (read-only) with:
--     SELECT id, seller_id, title, price FROM waste2value_final.diy_products WHERE price < 0;
-- then decide how to fix them before running this again.
--
-- Requires MySQL 8.0.16+ for the constraint to be enforced; older MySQL
-- accepts but ignores CHECK. The application validates prices regardless.
--
-- Run:  mysql -u root -p < database/migrations/002_diy_products_price_check.sql
-- =====================================================================

USE `waste2value_final`;

SET @has_check := (
    SELECT COUNT(*) FROM information_schema.TABLE_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = DATABASE()
      AND TABLE_NAME = 'diy_products'
      AND CONSTRAINT_NAME = 'chk_diy_products_price'
);

SET @ddl := IF(@has_check = 0,
    'ALTER TABLE `diy_products` ADD CONSTRAINT `chk_diy_products_price` CHECK (`price` >= 0)',
    'DO 0');

PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
