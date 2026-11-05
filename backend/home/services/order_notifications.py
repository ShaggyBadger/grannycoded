"""Email the shop owner and the customer when a paid order arrives.

Sending is best effort. A mail failure must never fail the Stripe webhook:
Stripe retries are de-duplicated, so a retried event would not resend the
message, and the order would be left with no notification at all.
"""

import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from oscar.core.loading import get_model
from oscar.templatetags.currency_filters import currency

logger = logging.getLogger(__name__)


def send_order_emails(order_number: str) -> None:
    """Send the customer receipt and the owner notification for one order."""
    if not settings.EMAIL_HOST:
        logger.info("Email is not configured; skipping order mail for %s", order_number)
        return

    Order = get_model("order", "Order")
    order = (
        Order.objects.select_related("shipping_address")
        .filter(number=order_number)
        .first()
    )
    if order is None:
        logger.error("Cannot email missing order %s", order_number)
        return

    context = _order_context(order)
    _send(
        template="customer_receipt",
        subject=f"Your GrannyCoded order {order.number}",
        context=context,
        recipient=order.email,
        description=f"customer receipt for {order.number}",
    )
    if settings.ORDER_NOTIFICATION_EMAIL:
        _send(
            template="new_order",
            subject=f"New order {order.number} — {context['total']}",
            context=context,
            recipient=settings.ORDER_NOTIFICATION_EMAIL,
            description=f"new-order notice for {order.number}",
        )
    else:
        logger.warning(
            "ORDER_NOTIFICATION_EMAIL is empty; no new-order notice sent for %s",
            order.number,
        )


def _order_context(order) -> dict:
    address = order.shipping_address
    payment = (
        order.payment_events.order_by("date_created")
        .values_list("reference", flat=True)
        .last()
    )
    return {
        "number": order.number,
        "placed": order.date_placed,
        "total": currency(order.total_incl_tax, order.currency),
        "customer_email": order.email,
        "greeting_name": (address.first_name if address else "") or "there",
        "address_lines": address.active_address_fields() if address else [],
        "lines": [
            {
                "title": line.title,
                "quantity": line.quantity,
                "line_total": currency(line.line_price_incl_tax, order.currency),
            }
            for line in order.lines.all()
        ],
        "payment_reference": payment or "no payment record",
        "dashboard_url": (
            f"{settings.PUBLIC_SITE_URL}/dashboard/orders/{order.number}/"
        ),
    }


def _send(*, template: str, subject: str, context: dict, recipient: str, description: str):
    if not recipient:
        logger.warning("No recipient for %s; nothing sent", description)
        return
    try:
        body = render_to_string(f"home/email/{template}.txt", context)
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
            fail_silently=False,
        )
        logger.info("Sent %s to %s", description, recipient)
    except (SMTPException, OSError):
        logger.exception("Could not send %s to %s", description, recipient)
