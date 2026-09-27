# Shared database

Both Flask apps use **one MySQL 8.0 database**. The integration database is currently
**`waste2value_admin_test`**.

Both apps must point at the same database. Check that these values match in
`flask_apps/main_app/.env` and `flask_apps/admin_app/.env`:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=<your MySQL password>
DB_NAME=waste2value_admin_test
```

## Tables and ownership

| Table | Owned by | Used by the admin app for |
|---|---|---|
| `users` | Main app (registration, profile) | Listing, searching, adding and editing users, and deleting users that have no activity |
| `listings` | Main app | Listing and searching, and status changes: remove, archive, restore |
| `offers` | Main app | Read-only: dashboard counts and listing details |
| `pickups` | Main app | Read-only: dashboard counts and listing details |
| `admins` | Admin app | Admin login (bcrypt passwords) |
| `recyclers` | Admin app | Managing recyclers |
| `complaints` | Admin app | Managing complaints (`user_id` → `users.id`) |

Listing status values: the main app only shows listings whose status is `available`. The
admin app adds `removed` and `archived`, which hide a listing without deleting it.

## Current state

`waste2value_admin_test` already contains all seven tables. **Nothing needs to be imported.**

To check it at any time (read-only):

```powershell
cd flask_apps\admin_app
flask --app app check-schema
```

Every table should report `ok`.

## Building a database from scratch

Only do this for a **new, empty** database. Neither script should be run over existing data.

1. Create the empty database, then import the application tables and demo data:

   ```powershell
   mysql -u root -p -e "CREATE DATABASE waste2value_admin_test"
   mysql -u root -p waste2value_admin_test < flask_apps\main_app\database_with_data.sql
   ```

2. Add the admin tables. The migration is additive and safe to re-run:

   ```powershell
   mysql -u root -p < flask_apps\admin_app\database.sql
   ```

   `database.sql` starts with `USE waste2value_admin_test;`. Change that line if you use a
   different database name.

3. Create an administrator and verify:

   ```powershell
   cd flask_apps\admin_app
   flask --app app create-admin
   flask --app app check-schema
   ```
