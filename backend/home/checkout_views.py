"""Public checkout views backed by Stripe-hosted Checkout."""

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from oscar.core.loading import get_model

from home.models import CheckoutLine, CheckoutSession
from home.services import stock_reservation, stripe_checkout

logger = logging.getLogger(__name__)

PARTNER_CODE = "grannycoded"


class BasketProblem(Exception):
    """The basket holds something that can no longer be bought."""


def _purchasable(product) -> bool:
    """True when the product (or its parent variant) is still on sale."""
    if product.is_public:
        return True
    parent = product.parent
    return bool(parent and parent.is_public)


def _basket_lines(basket):
    """Return buyable lines plus any problems found, without raising."""
    lines, problems = [], []
    for line in basket.all_lines():
        product = line.product
        if not _purchasable(product):
            problems.append(
                f"{product.get_title()} is no longer available. "
                "Remove it from your cart to continue."
            )
            continue
        unit_price = line.price_incl_tax
        if unit_price is None:
            unit_price = line.price_excl_tax
        lines.append((product, line.quantity, Decimal(unit_price), line.price_currency))
    return lines, problems


def _partner_sku(product) -> str:
    StockRecord = get_model("partner", "StockRecord")
    record = (
        StockRecord.objects.filter(product=product, partner__code=PARTNER_CODE)
        .values_list("partner_sku", flat=True)
        .first()
    )
    return record or ""


def _render_summary(request, *, error=None, status=200):
    basket = request.basket
    lines, problems = _basket_lines(basket)
    rows = [
        {
            "title": product.get_title(),
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": unit_price * quantity,
            "currency": currency,
            "url": product.get_absolute_url(),
        }
        for product, quantity, unit_price, currency in lines
    ]
    total = sum((row["line_total"] for row in rows), Decimal("0.00"))
    return render(
        request,
        "home/checkout_payment.html",
        {
            "lines": rows,
            "total": total,
            "currency": basket.currency,
            "stripe_enabled": settings.STRIPE_ENABLED,
            "error": error or " ".join(problems) or None,
        },
        status=status,
    )


@require_GET
def payment_summary(request):
    """Show the order summary and the Stripe explanation before redirecting."""
    if not settings.STRIPE_ENABLED:
        return render(request, "home/checkout_unavailable.html", status=200)
    if request.basket.is_empty:
        return redirect("basket:summary")
    try:
        return _render_summary(request)
    except BasketProblem as error:
        return _render_summary(request, error=str(error), status=409)


@require_POST
def start_checkout(request):
    """Snapshot the basket, hold stock, and redirect to Stripe."""
    if not settings.STRIPE_ENABLED:
        return render(request, "home/checkout_unavailable.html", status=200)

    basket = request.basket
    if basket.is_empty:
        return redirect("basket:summary")

    stock_reservation.release_expired()
    lines, problems = _basket_lines(basket)
    if problems:
        return _render_summary(request, error=" ".join(problems), status=409)

    if not lines:
        return redirect("basket:summary")

    try:
        with transaction.atomic():
            session = CheckoutSession.objects.create(
                basket_id=basket.pk,
                currency=basket.currency or "usd",
                total_incl_tax=sum(
                    (unit_price * quantity for _, quantity, unit_price, _ in lines),
                    Decimal("0.00"),
                ),
                expires_at=timezone.now()
                + timedelta(minutes=settings.STRIPE_CHECKOUT_EXPIRY_MINUTES),
            )
            for product, quantity, unit_price, currency in lines:
                CheckoutLine.objects.create(
                    session=session,
                    product=product,
                    product_title=product.get_title(),
                    partner_sku=_partner_sku(product),
                    quantity=quantity,
                    unit_price_incl_tax=unit_price,
                    currency=currency,
                )
            stock_reservation.reserve_for_session(
                session, [(product, quantity) for product, quantity, _, _ in lines]
            )
    except stock_reservation.InsufficientStock as error:
        logger.info("Checkout refused: %s", error)
        return _render_summary(request, error=str(error), status=409)

    success_url = (
        request.build_absolute_uri(reverse("checkout:complete"))
        + "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = request.build_absolute_uri(reverse("basket:summary"))

    try:
        url = stripe_checkout.create_checkout_session(
            session, success_url=success_url, cancel_url=cancel_url
        )
    except stripe_checkout.PaymentsUnavailable:
        logger.exception("Could not open a Stripe session for %s", session.pk)
        session.status = CheckoutSession.Status.FAILED
        session.save(update_fields=["status", "updated_at"])
        stock_reservation.release_session(session)
        return _render_summary(
            request,
            error="We could not open the secure payment page. Please try again.",
            status=502,
        )

    return redirect(url)


@require_GET
def complete(request):
    """Confirm a finished payment using our own record, not the query string."""
    session_id = request.GET.get("session_id", "").strip()
    attempt = (
        CheckoutSession.objects.filter(stripe_session_id=session_id).first()
        if session_id
        else None
    )
    Order = get_model("order", "Order")
    order = (
        Order.objects.filter(number=attempt.order_number).first()
        if attempt and attempt.order_number
        else None
    )
    return render(
        request,
        "home/checkout_complete.html",
        {
            "attempt": attempt,
            "order": order,
            "pending": bool(attempt and attempt.status == CheckoutSession.Status.PENDING),
            "failed": bool(
                attempt
                and attempt.status
                in (CheckoutSession.Status.FAILED, CheckoutSession.Status.EXPIRED)
            ),
        },
        status=200,
    )


@require_GET
def payment_security(request):
    return render(request, "home/payment_security.html")


@csrf_exempt
@require_POST
def webhook(request):
    """Receive Stripe events. Authenticated by signature only."""
    payload = request.body
    signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe_checkout.verify_webhook(payload, signature)
    except stripe_checkout.PaymentsUnavailable as error:
        logger.error("Stripe webhook rejected: %s", error)
        return HttpResponse(status=400)
    except Exception:  # stripe.SignatureVerificationError
        logger.warning("Stripe webhook signature verification failed")
        return HttpResponse(status=400)

    try:
        outcome = stripe_checkout.process_event(event)
    except Exception:
        logger.exception("Stripe webhook %s failed to process", event.get("id"))
        # A 5xx makes Stripe retry, which is what we want for a transient error.
        return HttpResponse(status=500)

    logger.info("Stripe webhook %s: %s", event.get("id"), outcome)
    return HttpResponse(status=200)
