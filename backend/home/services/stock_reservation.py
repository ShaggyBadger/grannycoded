"""Hold stock for open Stripe Checkout attempts.

A Stripe payment page can stay open for up to half an hour, which is long
enough for a one-of-a-kind piece to sell twice. Reservations close that gap:
available stock is the partner balance minus unallocated stock minus every
reservation that has not expired or been released.
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from oscar.core.loading import get_model

from home.models import StockReservation

PARTNER_CODE = "grannycoded"


class InsufficientStock(Exception):
    """Raised when a line asks for more stock than is available right now."""

    def __init__(self, title: str, available: int, requested: int):
        self.title = title
        self.available = max(available, 0)
        self.requested = requested
        super().__init__(
            f"{title} has {max(available, 0)} available; {requested} requested."
        )


def _stock_records(product_ids):
    StockRecord = get_model("partner", "StockRecord")
    return {
        record.product_id: record
        for record in StockRecord.objects.select_for_update()
        .filter(product_id__in=product_ids, partner__code=PARTNER_CODE)
        .order_by("pk")
    }


def _held_quantities(product_ids, now, session=None) -> dict[int, int]:
    """Quantity of each product held by unexpired reservations."""
    reservations = StockReservation.objects.filter(
        product_id__in=product_ids,
        released_at__isnull=True,
        expires_at__gt=now,
    )
    if session is not None:
        reservations = reservations.exclude(session=session)
    return {
        row["product_id"]: row["held"] or 0
        for row in reservations.values("product_id").annotate(held=Sum("quantity"))
    }


def available_quantities(products, session=None) -> dict[int, int]:
    """Return sellable stock per product id, after reservations."""
    product_ids = [product.pk for product in products]
    if not product_ids:
        return {}
    now = timezone.now()
    records = _stock_records(product_ids)
    held = _held_quantities(product_ids, now, session=session)
    available = {}
    for product_id in product_ids:
        record = records.get(product_id)
        if record is None:
            available[product_id] = 0
            continue
        balance = (record.num_in_stock or 0) - (record.num_allocated or 0)
        available[product_id] = max(balance - held.get(product_id, 0), 0)
    return available


def available_quantity(product, session=None) -> int:
    return available_quantities([product], session=session).get(product.pk, 0)


@transaction.atomic
def reserve_for_session(session, line_items) -> list[StockReservation]:
    """Validate and hold stock for every line of a checkout attempt.

    ``line_items`` is an iterable of ``(product, quantity)`` pairs. Raises
    :class:`InsufficientStock` before writing anything if any line cannot be
    satisfied.
    """
    quantities: dict[int, int] = {}
    product_by_id = {}
    for product, quantity in line_items:
        if quantity < 1:
            raise InsufficientStock(product.get_title(), 0, quantity)
        product_by_id[product.pk] = product
        quantities[product.pk] = quantities.get(product.pk, 0) + quantity
    if not quantities:
        return []

    now = timezone.now()
    available = available_quantities(product_by_id.values(), session=session)
    for product_id, quantity in quantities.items():
        if quantity > available.get(product_id, 0):
            product = product_by_id[product_id]
            raise InsufficientStock(
                product.get_title(), available.get(product_id, 0), quantity
            )

    expires_at = now + timedelta(minutes=settings.STRIPE_CHECKOUT_EXPIRY_MINUTES)
    return [
        StockReservation.objects.create(
            session=session,
            product=product_by_id[product_id],
            quantity=quantity,
            expires_at=expires_at,
        )
        for product_id, quantity in quantities.items()
    ]


@transaction.atomic
def release_session(session) -> int:
    """Release every open reservation belonging to a checkout attempt."""
    now = timezone.now()
    return StockReservation.objects.filter(
        session=session, released_at__isnull=True
    ).update(released_at=now)


def release_expired() -> int:
    """Release reservations whose payment window has closed."""
    now = timezone.now()
    return StockReservation.objects.filter(
        released_at__isnull=True, expires_at__lte=now
    ).update(released_at=now)
