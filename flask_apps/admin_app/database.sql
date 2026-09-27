-- =====================================================================
-- WASTE2VALUE - MODULE 4 (ADMIN DASHBOARD) - ADDITIVE MIGRATION
-- =====================================================================
--
-- Run this AGAINST THE EXISTING Waste2Value application database, after the
-- application schema (users, listings, offers, pickups) has been imported
-- from the main application's database_with_data.sql.
--
-- This file only creates the tables that Module 4 owns:
--     admins, recyclers, complaints
--
-- It deliberately does NOT create, alter, drop or insert into:
--     users, listings, offers, pickups
-- Those belong to the main application and are only READ by Module 4
-- (plus admin status/role updates made through the dashboard).
--
-- Safe to run more than once: every statement uses IF NOT EXISTS and no
-- statement drops or deletes anything.
--
-- The database name below must match DB_NAME in Module 4's .env.
-- =====================================================================

USE waste2value_admin_test;


-- ---------------------------------------------------------------------
-- ADMINS: accounts allowed to log into the Admin Dashboard.
-- Kept separate from `users` so the public registration form of the main
-- application can never create an administrator.
-- There is no public sign-up: create admins with
--     flask --app app create-admin
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `admins` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(50) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_admins_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
-- RECYCLERS: recycling partners managed by administrators.
-- status: 'Pending' | 'Verified' | 'Rejected'
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `recyclers` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `recycler_name` VARCHAR(100) NOT NULL,
  `company` VARCHAR(150) DEFAULT NULL,
  `location` VARCHAR(100) DEFAULT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'Pending',
  PRIMARY KEY (`id`),
  KEY `idx_recyclers_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


-- ---------------------------------------------------------------------
-- COMPLAINTS: linked to the real application user through user_id.
-- status: 'Open' | 'Resolved' | 'Archived'
-- ON DELETE RESTRICT keeps complaint history from being orphaned.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `complaints` (
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
