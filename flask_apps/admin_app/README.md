# Waste2Value – Module 4: Admin Dashboard

A standalone Flask app (port **5001**) for administrators. It reads the Waste2Value
application data (`users`, `listings`, `offers`, `pickups`) and manages its own
tables (`admins`, `recyclers`, `complaints`).

## Setup

1. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Configure: copy `.env.example` to `.env`, set `ADMIN_SECRET_KEY`, and point the
   `DB_*` values at the **existing** Waste2Value application database.

3. Make sure the application schema (`users`, `listings`, `offers`, `pickups`) is
   already in that database (it comes from the main app's `database_with_data.sql`),
   then apply Module 4's additive migration:

   ```
   mysql -u root -p waste2value < database.sql
   ```

   It only creates `admins`, `recyclers`, `complaints` (`IF NOT EXISTS`). It never
   drops, alters or deletes anything.

4. Check the schema and create the first administrator (there is no public admin
   registration):

   ```
   flask --app app check-schema
   flask --app app create-admin
   ```

5. Run:

   ```
   python app.py
   ```

   Then open http://127.0.0.1:5001/.

## Note on older prototype tables

If the database was previously set up with the old prototype `database.sql`, it may
contain an old `complaints` table with a `user_name` column and no `user_id`.
`CREATE TABLE IF NOT EXISTS` will not replace it. `flask --app app check-schema` (or
`/db-test` when logged in) reports this as missing columns. Rename or migrate that old
table manually; Module 4 never drops tables itself.
