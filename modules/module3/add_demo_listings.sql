-- Run this against your EXISTING waste2value database (no need to re-import everything).
-- It clears the odd screenshot image on your current listing and adds 3 more demo
-- listings so the marketplace looks like the reference design with 4 cards.

UPDATE listings SET image_path = NULL WHERE id = 3;

INSERT INTO listings (seller_id, title, category, description, price, item_condition, image_path, status, created_at) VALUES
(12, 'newspaper bundle', 'paper', '', 50.00, 'used', NULL, 'available', NOW()),
(12, 'glass jar (clean)', 'glass', '', 80.00, 'used', NULL, 'available', NOW()),
(12, 'cardboard box', 'cardboard', '', 60.00, 'used', NULL, 'available', NOW());
