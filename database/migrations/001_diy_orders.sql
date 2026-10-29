-- =====================================================================
-- WASTE2VALUE - MIGRATION 001: DIY marketplace orders
-- =====================================================================
--
-- Upgrades an EXISTING `waste2value_final` database (created from an
-- earlier database/waste2value_final_schema.sql) so the handmade shop can
-- take orders. Fresh installs don't need this file: the updated
-- waste2value_final_schema.sql already contains the same changes.
--
-- What it does (additive only):
--   1. Adds diy_products.status  varchar(20) NOT NULL DEFAULT 'available'
--      (+ index). Existing products become 'available'.
--   2. Creates the diy_orders table.
--
-- What it never does: drop, rename, delete or update any existing row,
-- column or table. users, listings, offers, pickups, admins, recyclers and
-- complaints are not touched. No sample data is inserted.
--
-- Safe to run more than once: step 1 checks information_schema first and
-- step 2 uses CREATE TABLE IF NOT EXISTS.
--
-- Requires MySQL 8.0.16+ (or MariaDB 10.2+) for the CHECK constraints to be
-- enforced; older servers accept but ignore them (the app checks the same
-- rules itself).
--
-- Run:  mysql -u root -p < database/migrations/001_diy_orders.sql
-- =====================================================================

USE `waste2value_final`;


-- ---------------------------------------------------------------------
-- 1. diy_products.status  (available | reserved | sold)
-- ---------------------------------------------------------------------
SET @has_status := (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'diy_products'
      AND COLUMN_NAME = 'status'
);

SET @ddl := IF(@has_status = 0,
    'ALTER TABLE `diy_products`
       ADD COLUMN `status` varchar(20) NOT NULL DEFAULT ''available'',
       ADD KEY `idx_diy_products_status` (`status`)',
    'DO 0');

PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ---------------------------------------------------------------------
-- 2. diy_orders  (identical to the definition in waste2value_final_schema.sql)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `diy_orders` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `order_number` varchar(20) NOT NULL,
  `product_id` int(11) NOT NULL,
  `buyer_id` int(11) NOT NULL,
  `seller_id` int(11) NOT NULL,
  `product_title` varchar(150) NOT NULL,
  `unit_price` decimal(10,2) NOT NULL,
  `quantity` int(11) NOT NULL DEFAULT 1,
  `total_amount` decimal(10,2) NOT NULL,
  `delivery_name` varchar(100) NOT NULL,
  `delivery_phone` varchar(10) NOT NULL,
  `address_line` varchar(255) NOT NULL,
  `locality` varchar(120) NOT NULL,
  `city` varchar(80) NOT NULL,
  `state` varchar(60) NOT NULL,
  `pincode` char(6) NOT NULL,
  `delivery_instructions` varchar(300) DEFAULT NULL,
  `payment_method` varchar(20) NOT NULL,
  `payment_status` varchar(20) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'placed',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_diy_orders_order_number` (`order_number`),
  KEY `idx_diy_orders_product_id` (`product_id`),
  KEY `idx_diy_orders_buyer_id` (`buyer_id`),
  KEY `idx_diy_orders_seller_id` (`seller_id`),
  KEY `idx_diy_orders_status` (`status`),
  CONSTRAINT `fk_diy_orders_product` FOREIGN KEY (`product_id`) REFERENCES `diy_products` (`id`),
  CONSTRAINT `fk_diy_orders_buyer` FOREIGN KEY (`buyer_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_diy_orders_seller` FOREIGN KEY (`seller_id`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_diy_orders_not_self` CHECK (`buyer_id` <> `seller_id`),
  CONSTRAINT `chk_diy_orders_quantity` CHECK (`quantity` = 1),
  CONSTRAINT `chk_diy_orders_amounts` CHECK (`unit_price` >= 0 AND `total_amount` = `unit_price` * `quantity`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
