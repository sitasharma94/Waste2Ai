# Waste2Value

Waste2Value is a recycling marketplace with an AI recycling assistant and an admin dashboard.

The project runs as **two separate Flask applications** that share **one MySQL database**:

| App | Folder | Port | What it is |
|---|---|---|---|
| Main app | `flask_apps/main_app/` | **5000** | Module 2. Marketplace: register and login, listings, offers, pickups, AI recycling assistant |
| Admin app | `flask_apps/admin_app/` | **5001** | Module 4. Admin dashboard: users, listings, recyclers, complaints |

The two apps are deliberately **not** merged into a single Flask app. They have different routes,
sessions, authentication and CSRF handling. They share data only through the database.

## Folder structure

```
Waste2Value/
├── flask_apps/
│   ├── main_app/     Module 2: main marketplace application (port 5000)
│   └── admin_app/    Module 4: admin dashboard (port 5001)
├── modules/
│   ├── module1/      Module 1: original marketplace, kept unchanged as reference
│   └── module3/      Module 3: kept unchanged as reference
├── database/
│   └── README.md     Shared database setup
└── README.md
```

`modules/` is for reference only. Module 2 already contains everything in Module 1, and
Module 3 is a copy of Module 2. Neither needs to be run.

## Requirements

- Python 3.12 or newer
- MySQL 8.0, with the shared database set up as described in [`database/README.md`](database/README.md)

Install the dependencies of both apps. One virtual environment for both is fine:

```powershell
pip install -r flask_apps/main_app/requirements.txt
pip install -r flask_apps/admin_app/requirements.txt
```

## Configuration (one time)

Each app reads its own `.env` file from its own folder. Create them from the examples:

```powershell
copy flask_apps\main_app\.env.example  flask_apps\main_app\.env
copy flask_apps\admin_app\.env.example flask_apps\admin_app\.env
```

Then edit both `.env` files:

- Set `DB_PASSWORD` to your MySQL password in **both** files.
- Set `DB_NAME` to the **same** database in both files (currently `waste2value_admin_test`).
- In `admin_app\.env`, set `ADMIN_SECRET_KEY` to a long random value:
  `python -c "import secrets; print(secrets.token_hex(32))"`

`.env` files contain secrets and are ignored by git (see `.gitignore`). Only commit the
`.env.example` files.

## Running

Use two terminals, one per app:

```powershell
# Terminal 1: main app  ->  http://127.0.0.1:5000/login
cd flask_apps\main_app
python app.py
```

```powershell
# Terminal 2: admin app  ->  http://127.0.0.1:5001/
cd flask_apps\admin_app
python app.py
```

No PowerShell environment variables are needed; both apps load their `.env` automatically.

The first time only, create an administrator account. There is no public admin sign-up:

```powershell
cd flask_apps\admin_app
flask --app app create-admin
```

## How the apps work together

- Users register, list items, make offers and schedule pickups in the **main app**. All of it is
  stored in `users`, `listings`, `offers` and `pickups`.
- The **admin app** reads those same tables. Admin actions write back to them, for example
  removing, archiving or restoring a listing, or editing a user's role, and the main app sees
  the changes immediately.
- Listing images are saved by the main app in `flask_apps/main_app/static/uploads/`. The admin
  app reads them from there to show them on the listing detail page.
