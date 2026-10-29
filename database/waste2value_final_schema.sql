-- =====================================================================
-- WASTE2VALUE - FINAL SHARED DATABASE SCHEMA (STRUCTURE ONLY, NO DATA)
-- =====================================================================
--
-- Creates the empty `waste2value_final` database used by both Flask apps:
--   flask_apps/main_app   (Modules 1-3: users, listings, offers, pickups,
--                          diy_products, diy_orders)
--   flask_apps/admin_app  (Module 4:    admins, recyclers, complaints)
--
-- Sources, copied without changes to columns, keys or constraints:
--   flask_apps/main_app/database_with_data.sql   (tables 1-4, data rows omitted)
--   flask_apps/admin_app/database.sql            (tables 5-7)
-- Tables 4b (diy_products) and 4c (diy_orders) are new and defined only here.
-- Existing installs upgrade with the files in database/migrations/, in order.
--
-- Every table starts empty and every AUTO_INCREMENT starts at 1.
--
-- Column ORDER matters: both apps read rows by position
-- (e.g. user[3] = password_hash, listing[7] = image_path). Do not reorder.
--
-- Safety: CREATE DATABASE and CREATE TABLE deliberately have no IF NOT EXISTS,
-- so the script stops with an error instead of reusing an existing database
-- or table. It never drops, alters or deletes anything.
--
-- Run:  mysql -u root -p < database/waste2value_final_schema.sql
-- =====================================================================

SET NAMES utf8mb4;

CREATE DATABASE `waste2value_final`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_general_ci;

USE `waste2value_final`;


-- ---------------------------------------------------------------------
-- 1. USERS (main app: registration, login, profile)
-- ---------------------------------------------------------------------
CREATE TABLE `users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` varchar(20) DEFAULT 'buyer',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
-- 2. LISTINGS (main app marketplace; admin app sets status
--    'available' / 'removed' / 'archived')
-- ---------------------------------------------------------------------
CREATE TABLE `listings` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `seller_id` int(11) NOT NULL,
  `title` varchar(150) NOT NULL,
  `category` varchar(50) NOT NULL,
  `description` text DEFAULT NULL,
  `price` decimal(10,2) NOT NULL,
  `item_condition` varchar(50) DEFAULT NULL,
  `image_path` varchar(255) DEFAULT NULL,
  `status` varchar(20) DEFAULT 'available',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `seller_id` (`seller_id`),
  CONSTRAINT `listings_ibfk_1` FOREIGN KEY (`seller_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
-- 3. OFFERS (buyer offers on listings)
-- ---------------------------------------------------------------------
CREATE TABLE `offers` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `listing_id` int(11) NOT NULL,
  `buyer_id` int(11) NOT NULL,
  `offer_price` decimal(10,2) NOT NULL,
  `status` varchar(20) DEFAULT 'pending',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `listing_id` (`listing_id`),
  KEY `buyer_id` (`buyer_id`),
  CONSTRAINT `offers_ibfk_1` FOREIGN KEY (`listing_id`) REFERENCES `listings` (`id`),
  CONSTRAINT `offers_ibfk_2` FOREIGN KEY (`buyer_id`) REFERENCES `users` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
-- 4. PICKUPS (scheduled for accepted offers)
-- ---------------------------------------------------------------------
CREATE TABLE `pickups` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `offer_id` int(11) NOT NULL,
  `address` varchar(255) NOT NULL,
  `pickup_date` date NOT NULL,
  `status` varchar(20) DEFAULT 'scheduled',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `offer_id` (`offer_id`),
  CONSTRAINT `pickups_ibfk_1` FOREIGN KEY (`offer_id`) REFERENCES `offers` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
-- 4b. DIY_PRODUCTS (main app /diy-marketplace: handmade / upcycled
--     products). Kept separate from `listings`: no offers or pickups.
--     image_path is relative to static/uploads/ (e.g. 'diy/<uuid>.jpg').
--     category: 'home-decor' | 'accessories' | 'art' | 'useful-recycled'
--     (validated by the app). The FK has the default RESTRICT behaviour, so
--     the admin app reports a seller with products as "referenced by other
--     records" instead of deleting them.
-- ---------------------------------------------------------------------
CREATE TABLE `diy_products` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `seller_id` int(11) NOT NULL,
  `title` varchar(150) NOT NULL,
  `description` text DEFAULT NULL,
  `price` decimal(10,2) NOT NULL,
  `category` varchar(50) NOT NULL,
  `image_path` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `status` varchar(20) NOT NULL DEFAULT 'available',
  PRIMARY KEY (`id`),
  KEY `idx_diy_products_seller_id` (`seller_id`),
  KEY `idx_diy_products_category` (`category`),
  KEY `idx_diy_products_status` (`status`),
  CONSTRAINT `fk_diy_products_seller` FOREIGN KEY (`seller_id`) REFERENCES `users` (`id`),
  CONSTRAINT `chk_diy_products_price` CHECK (`price` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
-- 4c. DIY_ORDERS (one item per order, bought from /diy-marketplace).
--     Product title and price are snapshotted so later product edits
--     never change an existing order. No card/UPI/bank details are stored.
--     status:         pending_payment | placed | confirmed | shipped | delivered | rejected | cancelled
--     payment_method: cod | free | upi_gpay | upi_phonepe | upi_paytm | card | netbanking
--     payment_status: cod_pending | not_required | not_charged | awaiting_payment | authorized
--                     | failed | expired | paid | refund_pending
--                     ('paid' is set only after Razorpay verifiably captured the payment)
--     courier_name / tracking_*: typed by the seller when shipping (not auto-tracked).
--     provider_*_id: Razorpay order/payment ids (unique, never card or bank data).
--     FKs use the default RESTRICT behaviour (no ON DELETE clause): MySQL does
--     not allow referential actions on columns used by the CHECK constraints.
-- ---------------------------------------------------------------------
CREATE TABLE `diy_orders` (
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
  `confirmed_at` timestamp NULL DEFAULT NULL,
  `shipped_at` timestamp NULL DEFAULT NULL,
  `delivered_at` timestamp NULL DEFAULT NULL,
  `closed_at` timestamp NULL DEFAULT NULL,
  `courier_name` varchar(100) DEFAULT NULL,
  `tracking_number` varchar(100) DEFAULT NULL,
  `tracking_url` varchar(500) DEFAULT NULL,
  `payment_provider` varchar(20) DEFAULT NULL,
  `provider_order_id` varchar(64) DEFAULT NULL,
  `provider_payment_id` varchar(64) DEFAULT NULL,
  `paid_at` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_diy_orders_order_number` (`order_number`),
  UNIQUE KEY `uq_diy_orders_provider_order_id` (`provider_order_id`),
  UNIQUE KEY `uq_diy_orders_provider_payment_id` (`provider_payment_id`),
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


-- ---------------------------------------------------------------------
-- 5. ADMINS (Module 4 login; separate from `users` so public
--    registration can never create an administrator).
--    Create accounts with:  flask --app app create-admin
-- ---------------------------------------------------------------------
CREATE TABLE `admins` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(50) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_admins_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
-- 6. RECYCLERS (Module 4)
-- ---------------------------------------------------------------------
CREATE TABLE `recyclers` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `recycler_name` VARCHAR(100) NOT NULL,
  `company` VARCHAR(150) DEFAULT NULL,
  `location` VARCHAR(100) DEFAULT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'Pending',
  PRIMARY KEY (`id`),
  KEY `idx_recyclers_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
-- 7. COMPLAINTS (Module 4; each complaint belongs to a user)
-- ---------------------------------------------------------------------
CREATE TABLE `complaints` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `subject` VARCHAR(150) NOT NULL,
  `description` TEXT DEFAULT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'Open',
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_complaints_user_id` (`user_id`),
  KEY `idx_complaints_status` (`status`),
  CONSTRAINT `fk_complaints_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
