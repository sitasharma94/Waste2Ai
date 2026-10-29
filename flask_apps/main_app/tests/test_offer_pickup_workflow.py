"""Offer and pickup workflow tests using an in-memory DB double only."""

import copy
import os
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace


# Importing the app must not read the developer's real .env during these tests.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
try:
    import dotenv
    dotenv.load_dotenv = lambda *args, **kwargs: False
except ImportError:
    pass

MAIN_APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MAIN_APP_DIR))
import app as waste2value_app  # noqa: E402


class MemoryConnection:
    def __init__(self):
        self.listings = {
            1: {"seller_id": 10, "status": "available"},
            2: {"seller_id": 10, "status": "available"},
        }
        self.offers = {}
        self.pickups = []
        self.display_rows = []
        self._snapshot = None
        self.commits = 0
        self.rollbacks = 0
        self.closed_cursors = 0

    def cursor(self):
        return MemoryCursor(self)

    def begin(self):
        self._snapshot = copy.deepcopy((self.listings, self.offers, self.pickups))

    def commit(self):
        self.commits += 1
        self._snapshot = None

    def rollback(self):
        self.rollbacks += 1
        if self._snapshot is not None:
            self.listings, self.offers, self.pickups = self._snapshot
            self._snapshot = None


class MemoryCursor:
    def __init__(self, connection):
        self.connection = connection
        self._rows = []
        self._index = 0
        self.rowcount = -1

    def execute(self, sql, params=()):
        query = " ".join(sql.lower().split())
        self._rows = []
        self._index = 0
        self.rowcount = -1

        if query.startswith("select offers.id, offers.listing_id"):
            self._rows = list(self.connection.display_rows)
        elif query.startswith("select seller_id, status from listings where id = %s"):
            listing = self.connection.listings.get(params[0])
            self._rows = [(listing["seller_id"], listing["status"])] if listing else []
        elif query.startswith("select listing_id from offers where id = %s"):
            offer = self.connection.offers.get(params[0])
            self._rows = [(offer["listing_id"],)] if offer else []
        elif query.startswith("select buyer_id, status from offers where id = %s and listing_id = %s"):
            offer = self.connection.offers.get(params[0])
            if offer and offer["listing_id"] == params[1]:
                self._rows = [(offer["buyer_id"], offer["status"])]
        elif query.startswith("select id from offers where listing_id = %s and status = 'accepted'"):
            self._rows = [
                (offer_id,) for offer_id, offer in self.connection.offers.items()
                if offer["listing_id"] == params[0] and offer["status"].lower() == "accepted"
            ]
        elif query.startswith("select id from pickups where offer_id = %s"):
            found = [pickup for pickup in self.connection.pickups if pickup["offer_id"] == params[0]]
            self._rows = [(found[-1]["id"],)] if found else []
        elif query.startswith("update offers set status = %s where id = %s and listing_id = %s"):
            offer = self.connection.offers.get(params[1])
            if offer and offer["listing_id"] == params[2] and offer["status"].lower() == "pending":
                offer["status"] = params[0]
                self.rowcount = 1
            else:
                self.rowcount = 0
        elif query.startswith("update offers set status = 'rejected'"):
            listing_id, accepted_offer_id = params
            changed = 0
            for offer_id, offer in self.connection.offers.items():
                if (offer["listing_id"] == listing_id and offer_id != accepted_offer_id
                        and offer["status"].lower() == "pending"):
                    offer["status"] = "rejected"
                    changed += 1
            self.rowcount = changed
        elif query.startswith("insert into offers"):
            listing_id, buyer_id, offer_price = params
            new_id = max(self.connection.offers, default=0) + 1
            self.connection.offers[new_id] = {
                "listing_id": listing_id, "buyer_id": buyer_id,
                "offer_price": offer_price, "status": "pending",
            }
            self.rowcount = 1
        elif query.startswith("insert into pickups"):
            offer_id, address, pickup_date = params
            new_id = max((p["id"] for p in self.connection.pickups), default=0) + 1
            self.connection.pickups.append({
                "id": new_id, "offer_id": offer_id,
                "address": address, "pickup_date": pickup_date,
                "status": "scheduled",
            })
            self.rowcount = 1
        else:
            raise AssertionError(f"Unexpected SQL in mocked test: {query}")

    def fetchone(self):
        if self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    def fetchall(self):
        rows = self._rows[self._index:]
        self._index = len(self._rows)
        return rows

    def close(self):
        self.connection.closed_cursors += 1


def offer_view_row(offer_id, listing_id, title, other_name, price, status,
                   listing_status="available", pickup_id=None, address=None,
                   pickup_date=None, pickup_status=None, offer_created=None,
                   pickup_created=None):
    return (offer_id, listing_id, title, other_name, price, status,
            listing_status, pickup_id, address, pickup_date, pickup_status,
            offer_created, pickup_created)


class OfferPickupWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.connection = MemoryConnection()
        self.original_mysql = waste2value_app.mysql
        waste2value_app.mysql = SimpleNamespace(connection=self.connection)
        self.client = waste2value_app.app.test_client()
        waste2value_app.app.config["TESTING"] = True
        self.addCleanup(self.restore_mysql)

    def restore_mysql(self):
        waste2value_app.mysql = self.original_mysql

    def sign_in(self, user_id=10, role="seller"):
        with self.client.session_transaction() as session:
            session["user_id"] = user_id
            session["user_role"] = role
            session["user_name"] = "Test User"

    def test_accept_closes_only_conflicting_pending_offers_and_keeps_history(self):
        self.connection.offers = {
            101: {"listing_id": 1, "buyer_id": 20, "offer_price": 50, "status": "pending"},
            102: {"listing_id": 1, "buyer_id": 21, "offer_price": 60, "status": "pending"},
            103: {"listing_id": 2, "buyer_id": 22, "offer_price": 70, "status": "pending"},
            104: {"listing_id": 1, "buyer_id": 23, "offer_price": 40, "status": "rejected"},
        }
        self.sign_in()

        response = self.client.post("/offer/respond/101", data={"action": "accepted"})

        self.assertEqual(response.status_code, 302)
        second_accept = self.client.post("/offer/respond/102", data={"action": "accepted"})
        self.assertEqual(second_accept.status_code, 302)
        self.assertEqual(self.connection.offers[101]["status"], "accepted")
        self.assertEqual(self.connection.offers[102]["status"], "rejected")
        self.assertEqual(self.connection.offers[103]["status"], "pending")
        self.assertEqual(self.connection.offers[104]["status"], "rejected")
        self.assertEqual(len(self.connection.offers), 4)
        self.assertEqual(self.connection.commits, 1)

    def test_rejected_history_and_old_pickup_date_warning_render(self):
        today = date.today()
        self.connection.display_rows = [
            offer_view_row(201, 1, "Glass bottles", "Buyer A", 25, "accepted",
                           pickup_id=3, address="12 Green Road",
                           pickup_date=today + timedelta(days=4), pickup_status="scheduled"),
            offer_view_row(202, 1, "Glass bottles", "Buyer B", 20, "rejected"),
            offer_view_row(203, 2, "Paper scraps", "Buyer C", 10, "accepted",
                           pickup_id=4, address="Old Street", pickup_date="2020-01-02",
                           pickup_status="scheduled"),
            offer_view_row(204, 1, "Glass bottles", "Buyer D", 22, "pending"),
            offer_view_row(205, 2, "Paper scraps", "Buyer E", 9, "pending",
                           listing_status="archived"),
        ]
        self.sign_in()

        response = self.client.get("/offers?type=received")
        page = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Active arrangement", page)
        self.assertIn("12 Green Road", page)
        self.assertIn("Offer History", page)
        self.assertIn("Offer declined.", page)
        self.assertIn("02 Jan 2020", page)
        self.assertIn("confirm whether the pickup occurred", page.lower())
        self.assertNotIn('value="accepted" type="submit">Accept</button>', page)
        self.assertEqual(self.connection.pickups, [])

    def test_buyer_and_non_owner_cannot_accept_or_schedule(self):
        self.connection.offers = {
            101: {"listing_id": 1, "buyer_id": 20, "offer_price": 50, "status": "accepted"},
        }

        self.sign_in(user_id=20, role="buyer")
        self.assertEqual(self.client.post("/offer/respond/101", data={"action": "rejected"}).status_code, 403)
        self.assertEqual(self.client.get("/pickup/schedule/101").status_code, 403)
        self.assertEqual(self.connection.pickups, [])

        self.sign_in(user_id=99, role="seller")
        self.assertEqual(self.client.post("/offer/respond/101", data={"action": "accepted"}).status_code, 403)
        self.assertEqual(self.client.get("/pickup/schedule/101").status_code, 403)
        self.assertEqual(self.connection.offers[101]["status"], "accepted")
        self.assertEqual(self.connection.pickups, [])

    def test_pickup_requires_future_date_and_keeps_seller_session(self):
        self.connection.offers = {
            101: {"listing_id": 1, "buyer_id": 20, "offer_price": 50, "status": "accepted"},
        }
        self.sign_in()
        bad = self.client.post("/pickup/schedule/101", data={
            "address": "12 Green Road", "pickup_date": "2020-01-01",
        })
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.connection.pickups, [])

        scheduled_for = (date.today() + timedelta(days=2)).isoformat()
        response = self.client.post("/pickup/schedule/101", data={
            "address": "12 Green Road", "pickup_date": scheduled_for,
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(self.connection.pickups), 1)
        self.assertEqual(self.connection.pickups[0]["address"], "12 Green Road")
        self.assertEqual(self.connection.pickups[0]["pickup_date"], date.fromisoformat(scheduled_for))
        with self.client.session_transaction() as session:
            self.assertEqual(session.get("user_id"), 10)
            self.assertEqual(session.get("user_role"), "seller")

    def test_legacy_invalid_pickup_dates_are_flagged_without_rewriting(self):
        today = date.today()
        past = waste2value_app._pickup_date_info("2020-01-02", today=today)
        invalid = waste2value_app._pickup_date_info("0000-00-00", today=today)

        self.assertEqual(past["state"], "past")
        self.assertIn("left unchanged", past["warning"])
        self.assertEqual(invalid["state"], "invalid")
        self.assertEqual(invalid["display"], "0000-00-00")
        self.assertEqual(self.connection.pickups, [])


if __name__ == "__main__":
    unittest.main()
