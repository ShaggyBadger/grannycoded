"""Create Stripe Checkout Sessions and fulfil them from webhook events.

Payment state is only ever taken from a signature-verified webhook, never from
the return URL, so a shopper cannot mark an order paid by editing a query
string.
"""

import json
import logging
from decimal import Decimal

import stripe
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.utils import timezone
from oscar.core.loading import get_class, get_model

from home.models import CheckoutSession, StripeEvent
from home.services import stock_reservation
from home.services.oscar_orders import create_oscar_order

logger = logging.getLogger(__name__)

ALLOWED_SHIPPING_COUNTRIES = ["US"]


class PaymentsUnavailable(Exception):
    """Stripe is not configured, or Stripe rejected the request."""


class FulfilmentFailed(Exception):
    """A paid session could not be turned into an Oscar order."""


def to_minor_units(amount: Decimal) -> int:
    return int((Decimal(amount) * 100).quantize(Decimal("1")))


def create_checkout_session(session: CheckoutSession, *, success_url: str, cancel_url: str):
    """Create the Stripe Checkout Session for a saved attempt and return its URL."""
    if not settings.STRIPE_ENABLED:
        raise PaymentsUnavailable("Stripe is not configured.")
    stripe.api_key = settings.STRIPE_SECRET_KEY

    lines = list(session.lines.all())
    if not lines:
        raise PaymentsUnavailable("This checkout attempt has no items.")

    params = {
        "mode": "payment",
        "client_reference_id": session.pk,
        "line_items": [
            {
                "quantity": line.quantity,
                "price_data": {
                    "currency": line.currency,
                    "unit_amount": to_minor_units(line.unit_price_incl_tax),
                    "product_data": {"name": line.product_title},
                },
            }
            for line in lines
        ],
        "expires_at": int(session.expires_at.timestamp()),
        "success_url": success_url,
        "cancel_url": cancel_url,
        "shipping_address_collection": {
            "allowed_countries": ALLOWED_SHIPPING_COUNTRIES
        },
        "metadata": {"checkout_session_id": session.pk},
        "payment_intent_data": {"metadata": {"checkout_session_id": session.pk}},
    }

    try:
        stripe_session = stripe.checkout.Session.create(
            **params, idempotency_key=session.pk
        )
    except stripe.StripeError as error:
        logger.exception("Stripe rejected checkout session %s", session.pk)
        raise PaymentsUnavailable(str(error)) from error

    session.stripe_session_id = stripe_session.id
    session.save(update_fields=["stripe_session_id", "updated_at"])
    return stripe_session.url


def verify_webhook(payload: bytes, signature: str) -> dict:
    """Verify Stripe's signature and return the event as a plain dict."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise PaymentsUnavailable("Stripe webhook secret is not configured.")
    stripe.WebhookSignature.verify_header(
        payload, signature, settings.STRIPE_WEBHOOK_SECRET, tolerance=300
    )
    return json.loads(payload)


def process_event(event) -> str:
    """Apply a verified Stripe event exactly once.

    Returns ``"processed"``, ``"duplicate"``, or ``"ignored"``.
    """
    event_id = event["id"]
    event_type = event["type"]

    with transaction.atomic():
        record = (
            StripeEvent.objects.select_for_update().filter(pk=event_id).first()
        )
        if record and record.processed_at:
            logger.info("Ignoring replayed Stripe event %s", event_id)
            return "duplicate"
        if record is None:
            record = StripeEvent.objects.create(id=event_id, event_type=event_type)

        handler = _HANDLERS.get(event_type)
        if handler is None:
            logger.info("No handler for Stripe event %s", event_type)
            return "ignored"

        handler(event["data"]["object"])

        record.processed_at = timezone.now()
        record.save(update_fields=["processed_at"])
    return "processed"


def _session_for(stripe_object) -> CheckoutSession | None:
    reference = (
        stripe_object.get("client_reference_id")
        or (stripe_object.get("metadata") or {}).get("checkout_session_id")
    )
    if not reference:
        logger.error("Stripe event carries no checkout reference")
        return None
    session = CheckoutSession.objects.filter(pk=reference).first()
    if session is None:
        logger.error("No checkout attempt matches reference %s", reference)
    return session


def _on_session_paid(stripe_object):
    session = _session_for(stripe_object)
    if session is None:
        return
    if session.status == CheckoutSession.Status.PAID:
        logger.info("Checkout %s is already paid", session.pk)
        return
    if session.status != CheckoutSession.Status.PENDING:
        logger.error(
            "Checkout %s is %s but Stripe reports payment",
            session.pk,
            session.status,
        )
        return
    _fulfil(session, stripe_object)


def _on_session_completed(stripe_object):
    if stripe_object.get("payment_status") != "paid":
        session = _session_for(stripe_object)
        logger.info(
            "Checkout %s completed without payment; waiting for confirmation",
            session.pk if session else "?",
        )
        return
    _on_session_paid(stripe_object)


def _on_session_expired(stripe_object):
    session = _session_for(stripe_object)
    if session is None or not session.is_open:
        return
    session.status = CheckoutSession.Status.EXPIRED
    session.save(update_fields=["status", "updated_at"])
    stock_reservation.release_session(session)


def _on_session_failed(stripe_object):
    session = _session_for(stripe_object)
    if session is None or not session.is_open:
        return
    session.status = CheckoutSession.Status.FAILED
    session.save(update_fields=["status", "updated_at"])
    stock_reservation.release_session(session)


def _system_request():
    """A request-shaped object so Oscar's order service can run from a webhook."""

    class SystemRequest:
        user = AnonymousUser()

        def __init__(self):
            self.strategy = get_class("partner.strategy", "Selector")().strategy(
                request=None, user=self.user
            )

        def get_host(self) -> str:
            return settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else "localhost"

    return SystemRequest()


def _shipping_details(stripe_object) -> dict:
    collected = stripe_object.get("collected_information") or {}
    return collected.get("shipping_details") or stripe_object.get(
        "shipping_details"
    ) or {}


def _shipping_address_from(stripe_object):
    details = _shipping_details(stripe_object)
    if not details:
        return None
    address_payload = details.get("address") or {}
    name = details.get("name") or ""
    ShippingAddress = get_model("order", "ShippingAddress")
    Country = get_model("address", "Country")
    country_code = (address_payload.get("country") or "").upper()
    country = Country.objects.filter(iso_3166_1_a2=country_code).first()
    if country is None:
        logger.warning("Unknown shipping country %r on Stripe session", country_code)
        return None
    first_name, _, last_name = name.partition(" ")
    return ShippingAddress(
        first_name=first_name or name,
        last_name=last_name,
        line1=address_payload.get("line1") or "",
        line2=address_payload.get("line2") or "",
        line4=address_payload.get("city") or "",
        state=address_payload.get("state") or "",
        postcode=address_payload.get("postal_code") or "",
        country=country,
    )


def _fulfil(session: CheckoutSession, stripe_object):
    """Turn a paid Stripe session into a completed Oscar order."""
    lines = list(session.lines.select_related("product"))
    missing = [line for line in lines if line.product_id is None]
    if not lines or missing:
        session.status = CheckoutSession.Status.FAILED
        session.save(update_fields=["status", "updated_at"])
        raise FulfilmentFailed(
            f"Checkout {session.pk} references a removed product and needs review."
        )

    customer_details = stripe_object.get("customer_details") or {}
    email = customer_details.get("email") or stripe_object.get("customer_email") or ""
    amount_total = stripe_object.get("amount_total")
    paid = (
        Decimal(amount_total) / 100
        if amount_total is not None
        else session.total_incl_tax
    )
    if amount_total is not None and paid != session.total_incl_tax:
        logger.warning(
            "Checkout %s charged %s but the basket was %s",
            session.pk,
            paid,
            session.total_incl_tax,
        )

    request = _system_request()
    address = _shipping_address_from(stripe_object)
    note = f"Paid online with Stripe. Amount {paid} {session.currency.upper()}."
    if address is None:
        note += " No usable shipping address was supplied; confirm it before dispatch."
        logger.warning("Checkout %s has no usable shipping address", session.pk)

    order = create_oscar_order(
        request,
        [(line.product, line.quantity) for line in lines],
        customer_email=email,
        shipping_address=address,
        note=note,
    )
    _record_payment(
        order,
        paid,
        reference=(stripe_object.get("payment_intent") or session.stripe_session_id),
    )

    details = _shipping_details(stripe_object)
    session.status = CheckoutSession.Status.PAID
    session.email = email
    session.order_number = order.number
    session.shipping_name = details.get("name", "")
    session.shipping_address = details.get("address", {})
    session.save(
        update_fields=[
            "status",
            "email",
            "order_number",
            "shipping_name",
            "shipping_address",
            "updated_at",
        ]
    )
    stock_reservation.release_session(session)
    return order


def _record_payment(order, amount: Decimal, reference: str):
    Order = get_model("order", "Order")
    PaymentEventType = get_model("order", "PaymentEventType")
    EventHandler = get_class("order.processing", "EventHandler")
    lines = list(order.lines.all())
    handler = EventHandler(user=AnonymousUser())
    handler.handle_payment_event(
        order,
        PaymentEventType.objects.get(code="paid"),
        amount=amount,
        lines=lines,
        line_quantities=[line.quantity for line in lines],
        reference=f"Stripe payment: {reference}",
    )
    order.set_status("Being processed")


_HANDLERS = {
    "checkout.session.completed": _on_session_completed,
    "checkout.session.async_payment_succeeded": _on_session_paid,
    "checkout.session.async_payment_failed": _on_session_failed,
    "checkout.session.expired": _on_session_expired,
}
