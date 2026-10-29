"""Razorpay integration for the DIY marketplace (hosted Checkout + server-side verification).

Configuration comes only from the environment (.env):
    RAZORPAY_KEY_ID          public key id (rzp_test_... or rzp_live_...)
    RAZORPAY_KEY_SECRET      secret key: server-side only, never sent to the browser or logged
    RAZORPAY_WEBHOOK_SECRET  secret set on the webhook in the Razorpay Dashboard (optional,
                             but needed to receive payment.captured / payment.failed events)

If the key id/secret are missing, or the `razorpay` package isn't installed, online
payments stay disabled and the app keeps working with Cash on Delivery and free items.

Nothing here marks an order as paid. It only answers "has Razorpay verifiably captured
the right amount for this Razorpay order?"; app.py decides what to do with the answer.
"""
import os
from decimal import Decimal

CURRENCY = 'INR'
MIN_AMOUNT = Decimal('1.00')   # Razorpay's minimum order amount is ₹1 (100 paise)

_client_factory = None         # tests replace this with a fake; never set in production


class GatewayUnavailable(Exception):
    """Online payments aren't configured, or Razorpay couldn't be reached."""


def _sdk():
    try:
        import razorpay
        return razorpay
    except ImportError:
        return None


def key_id():
    return os.environ.get('RAZORPAY_KEY_ID', '').strip()


def _key_secret():
    return os.environ.get('RAZORPAY_KEY_SECRET', '').strip()


def webhook_secret():
    return os.environ.get('RAZORPAY_WEBHOOK_SECRET', '').strip()


def is_configured():
    """True only when both API keys are present and the SDK is importable."""
    return bool(key_id() and _key_secret() and (_client_factory or _sdk()))


def is_test_mode():
    return key_id().startswith('rzp_test_')


def simulation_enabled():
    """Offer the clearly labelled 'Demo Payment (simulation only)' option?

    By default only while Razorpay is NOT configured (so a real deployment with
    keys never shows it). DIY_PAYMENT_SIMULATION=0 turns it off, =1 forces it on.
    A simulated payment is never treated as paid: app.py records it as
    payment_status='simulated' and nothing here can verify it.
    """
    flag = os.environ.get('DIY_PAYMENT_SIMULATION', '').strip().lower()
    if flag in ('0', 'false', 'off', 'no'):
        return False
    if flag in ('1', 'true', 'on', 'yes'):
        return True
    return not is_configured()


def unavailable_reason():
    if not (key_id() and _key_secret()):
        return "Online payments aren't set up on this site yet."
    if not (_client_factory or _sdk()):
        return "Online payments aren't available right now (payment library not installed)."
    return None


def client():
    if not is_configured():
        raise GatewayUnavailable(unavailable_reason())
    if _client_factory:
        return _client_factory()
    return _sdk().Client(auth=(key_id(), _key_secret()))


def to_paise(amount):
    """Exact Decimal rupees -> integer paise (Razorpay amounts are in the smallest unit)."""
    paise = (Decimal(amount) * 100)
    if paise != paise.to_integral_value():
        raise ValueError("amount has more than 2 decimal places")
    return int(paise)


def create_order(amount, receipt, notes):
    """Create a Razorpay order for `amount` rupees. Returns the Razorpay order id."""
    try:
        order = client().order.create(data={
            'amount': to_paise(amount),
            'currency': CURRENCY,
            'receipt': receipt[:40],
            'notes': notes,
        })
    except GatewayUnavailable:
        raise
    except Exception as err:  # network / API errors: never leak details to the buyer
        raise GatewayUnavailable("Couldn't start the online payment. Please try again.") from err
    if not order.get('id') or order.get('amount') != to_paise(amount) or order.get('currency') != CURRENCY:
        raise GatewayUnavailable("Razorpay returned an unexpected order.")
    return order['id']


def verify_checkout_signature(rzp_order_id, rzp_payment_id, signature):
    """True if the Checkout handler's signature is genuine (HMAC with the key secret)."""
    if not (rzp_order_id and rzp_payment_id and signature):
        return False
    try:
        client().utility.verify_payment_signature({
            'razorpay_order_id': rzp_order_id,
            'razorpay_payment_id': rzp_payment_id,
            'razorpay_signature': signature,
        })
        return True
    except GatewayUnavailable:
        raise
    except Exception:  # razorpay.errors.SignatureVerificationError (and malformed input)
        return False


def verify_webhook(raw_body, signature):
    """True if a webhook body was signed with RAZORPAY_WEBHOOK_SECRET."""
    secret = webhook_secret()
    if not (secret and signature):
        return False
    try:
        client().utility.verify_webhook_signature(raw_body, signature, secret)
        return True
    except GatewayUnavailable:
        raise
    except Exception:
        return False


def captured_payment(rzp_order_id, expected_amount):
    """Ask Razorpay (trusted server-to-server call) for a captured payment on this order.

    Returns (state, payment_id):
      ('captured', id)    a payment for exactly the expected amount + currency was captured
      ('authorized', id)  authorised but not yet captured (enable auto-capture in the Dashboard)
      ('failed', None)    every attempt so far failed
      ('none', None)      no payment attempt yet
    Raises GatewayUnavailable if Razorpay can't be reached.
    """
    try:
        items = client().order.payments(rzp_order_id).get('items', [])
    except GatewayUnavailable:
        raise
    except Exception as err:
        raise GatewayUnavailable("Couldn't reach Razorpay to check the payment.") from err

    expected = to_paise(expected_amount)
    matching = [p for p in items
                if p.get('order_id') == rzp_order_id and p.get('amount') == expected
                and p.get('currency') == CURRENCY]
    for status in ('captured', 'authorized'):
        for p in matching:
            if p.get('status') == status:
                return status, p.get('id')
    if items and all(p.get('status') == 'failed' for p in items):
        return 'failed', None
    return 'none', None
