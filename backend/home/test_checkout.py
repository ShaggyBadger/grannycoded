"""Checkout, stock reservation, and Stripe webhook tests."""

import hashlib
import hmac
import json
import time
from smtplib import SMTPException
from decimal import Decimal
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from oscar.core.loading import get_model

from home.models import CheckoutLine, CheckoutSession, StockReservation, StripeEvent
from home.services import stock_reservation

STRIPE_TEST_SETTINGS = {
    "STRIPE_ENABLED": True,
    "STRIPE_SECRET_KEY": "sk_test_unit",
    "STRIPE_WEBHOOK_SECRET": "whsec_unit",
    "STRIPE_CHECKOUT_EXPIRY_MINUTES": 35,
}


class CheckoutTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.Product = get_model("catalogue", "Product")
        cls.StockRecord = get_model("partner", "StockRecord")
        cls.product_class = get_model("catalogue", "ProductClass").objects.get(
            slug="handmade-goods"
        )
        cls.partner = get_model("partner", "Partner").objects.get(code="grannycoded")
        cls.category = get_model("catalogue", "Category").objects.get(
            slug="wearables"
        )
        Country = get_model("address", "Country")
        Country.objects.get_or_create(
            iso_3166_1_a2="US",
            defaults={
                "iso_3166_1_a3": "USA",
                "iso_3166_1_numeric": "840",
                "printable_name": "United States",
                "name": "United States of America",
                "is_shipping_country": True,
            },
        )

    def create_product(
        self,
        *,
        slug="mimi-quilt-coat",
        title="Mimi Quilt Coat",
        price=Decimal("179.00"),
        stock=1,
        is_public=True,
    ):
        product = self.Product.objects.create(
            title=title,
            slug=slug,
            description="A handmade piece created from a found quilt.",
            product_class=self.product_class,
            is_public=is_public,
        )
        product.categories.add(self.category)
        self.StockRecord.objects.create(
            product=product,
            partner=self.partner,
            partner_sku=slug,
            price_currency="USD",
            price=price,
            num_in_stock=stock,
            num_allocated=0,
        )
        return product

    def add_to_basket(self, product, quantity=1):
        response = self.client.post(
            reverse("basket:add", kwargs={"pk": product.pk}),
            {"quantity": quantity},
        )
        self.assertEqual(response.status_code, 302)

    def make_session(self, product, quantity=1, minutes=35):
        session = CheckoutSession.objects.create(
            currency="usd",
            total_incl_tax=Decimal("179.00") * quantity,
            expires_at=timezone.now() + timezone.timedelta(minutes=minutes),
        )
        CheckoutLine.objects.create(
            session=session,
            product=product,
            product_title=product.get_title(),
            partner_sku=product.slug,
            quantity=quantity,
            unit_price_incl_tax=Decimal("179.00"),
            currency="usd",
        )
        stock_reservation.reserve_for_session(session, [(product, quantity)])
        return session


class CheckoutPageTests(CheckoutTestBase):
    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_summary_lists_items_and_explains_stripe(self):
        product = self.create_product()
        self.add_to_basket(product)

        response = self.client.get(reverse("checkout:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mimi Quilt Coat")
        self.assertContains(response, "Payment handled by Stripe")
        self.assertContains(response, "never sees or stores your card number")
        self.assertContains(response, "Continue to secure payment")
        self.assertContains(response, 'class="assurance-more arrow-link"')
        self.assertContains(
            response, reverse("checkout:payment_security")
        )

    @override_settings(STRIPE_ENABLED=False, STRIPE_SECRET_KEY="")
    def test_checkout_is_closed_without_stripe_keys(self):
        product = self.create_product()
        self.add_to_basket(product)

        response = self.client.get(reverse("checkout:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Online checkout is opening soon")

    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_empty_basket_returns_to_cart(self):
        response = self.client.get(reverse("checkout:index"))

        self.assertRedirects(response, reverse("basket:summary"))

    def test_payment_security_page_is_public(self):
        response = self.client.get(reverse("checkout:payment_security"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "checkout.stripe.com")


class StockReservationTests(CheckoutTestBase):
    def test_second_shopper_cannot_reserve_a_one_of_a_kind(self):
        product = self.create_product(stock=1)
        first = self.make_session(product)

        self.assertEqual(stock_reservation.available_quantity(product), 0)
        second = CheckoutSession.objects.create(
            currency="usd",
            total_incl_tax=Decimal("179.00"),
            expires_at=timezone.now() + timezone.timedelta(minutes=35),
        )
        with self.assertRaises(stock_reservation.InsufficientStock):
            stock_reservation.reserve_for_session(second, [(product, 1)])

        self.assertEqual(StockReservation.objects.filter(session=first).count(), 1)
        self.assertFalse(StockReservation.objects.filter(session=second).exists())

    def test_expired_reservation_frees_stock(self):
        product = self.create_product(stock=1)
        session = self.make_session(product)
        StockReservation.objects.filter(session=session).update(
            expires_at=timezone.now() - timezone.timedelta(minutes=1)
        )

        self.assertEqual(stock_reservation.available_quantity(product), 1)
        self.assertEqual(stock_reservation.release_expired(), 1)

    def test_batch_stock_is_shared(self):
        product = self.create_product(stock=3)
        self.make_session(product, quantity=2)

        self.assertEqual(stock_reservation.available_quantity(product), 1)


class StartCheckoutTests(CheckoutTestBase):
    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_start_snapshots_basket_and_redirects_to_stripe(self):
        product = self.create_product(price=Decimal("149.00"))
        self.add_to_basket(product)

        with patch("stripe.checkout.Session.create") as create:
            create.return_value = type(
                "StripeSession", (), {"id": "cs_test_1", "url": "https://stripe.test/pay"}
            )()

            response = self.client.post(reverse("checkout:start"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://stripe.test/pay")
        session = CheckoutSession.objects.get()
        self.assertEqual(session.stripe_session_id, "cs_test_1")
        self.assertEqual(session.total_incl_tax, Decimal("149.00"))
        self.assertEqual(session.lines.get().product_title, "Mimi Quilt Coat")
        self.assertEqual(stock_reservation.available_quantity(product), 0)
        self.assertEqual(
            create.call_args.kwargs["line_items"][0]["price_data"]["unit_amount"], 14900
        )

    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_withdrawn_product_is_refused(self):
        product = self.create_product()
        self.add_to_basket(product)
        self.Product.objects.filter(pk=product.pk).update(is_public=False)

        with patch("stripe.checkout.Session.create") as create:
            response = self.client.post(reverse("checkout:start"))

        self.assertEqual(response.status_code, 409)
        self.assertContains(response, "no longer available", status_code=409)
        create.assert_not_called()
        self.assertFalse(CheckoutSession.objects.exists())


class WebhookTests(CheckoutTestBase):
    def _event(self, session, **overrides):
        payload = {
            "id": "evt_test_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": session.stripe_session_id or "cs_test_1",
                    "client_reference_id": session.pk,
                    "payment_status": "paid",
                    "payment_intent": "pi_test_1",
                    "amount_total": 17900,
                    "customer_details": {"email": "shopper@example.com"},
                    "collected_information": {
                        "shipping_details": {
                            "name": "Mary Ballard",
                            "address": {
                                "line1": "12 Quilt Lane",
                                "city": "Raleigh",
                                "state": "NC",
                                "postal_code": "27601",
                                "country": "US",
                            },
                        }
                    },
                }
            },
        }
        payload.update(overrides)
        return payload

    def _post(self, payload, secret="whsec_unit", timestamp=None):
        body = json.dumps(payload).encode()
        timestamp = timestamp or int(time.time())
        signature = hmac.new(
            secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
        ).hexdigest()
        return self.client.post(
            reverse("checkout:webhook"),
            data=body,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=f"t={timestamp},v1={signature}",
        )

    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_paid_event_creates_order_once_and_releases_stock(self):
        product = self.create_product(stock=1)
        session = self.make_session(product)
        session.stripe_session_id = "cs_test_1"
        session.save(update_fields=["stripe_session_id"])

        response = self._post(self._event(session))

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, CheckoutSession.Status.PAID)
        self.assertTrue(session.order_number)
        self.assertEqual(session.email, "shopper@example.com")
        Order = get_model("order", "Order")
        order = Order.objects.get(number=session.order_number)
        self.assertEqual(order.total_incl_tax, Decimal("179.00"))
        self.assertEqual(order.shipping_address.line1, "12 Quilt Lane")
        self.assertEqual(order.shipping_address.country.iso_3166_1_a2, "US")
        record = self.StockRecord.objects.get(product=product)
        self.assertEqual(record.num_allocated, 1)
        self.assertFalse(
            StockReservation.objects.filter(
                session=session, released_at__isnull=True
            ).exists()
        )

    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_replayed_event_does_not_create_a_second_order(self):
        product = self.create_product(stock=1)
        session = self.make_session(product)
        payload = self._event(session)

        self.assertEqual(self._post(payload).status_code, 200)
        self.assertEqual(self._post(payload).status_code, 200)

        Order = get_model("order", "Order")
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(StripeEvent.objects.count(), 1)

    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_invalid_signature_is_rejected(self):
        product = self.create_product(stock=1)
        session = self.make_session(product)

        response = self._post(self._event(session), secret="whsec_wrong")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(StripeEvent.objects.exists())
        session.refresh_from_db()
        self.assertEqual(session.status, CheckoutSession.Status.PENDING)

    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_expired_session_releases_stock(self):
        product = self.create_product(stock=1)
        session = self.make_session(product)
        payload = self._event(session, type="checkout.session.expired")

        response = self._post(payload)

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, CheckoutSession.Status.EXPIRED)
        self.assertEqual(stock_reservation.available_quantity(product), 1)

    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_confirmation_page_renders_the_order_after_payment(self):
        product = self.create_product(stock=1)
        session = self.make_session(product)
        session.stripe_session_id = "cs_test_1"
        session.save(update_fields=["stripe_session_id"])

        self.assertEqual(self._post(self._event(session)).status_code, 200)
        session.refresh_from_db()

        page = self.client.get(
            reverse("checkout:complete"), {"session_id": "cs_test_1"}
        )

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, session.order_number)
        self.assertContains(page, "Thank you.")
        self.assertContains(page, "$179.00")
        self.assertContains(page, "Check your email")
        self.assertContains(page, "shopper@example.com")
        self.assertContains(page, "spam or junk folder")

    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_confirmation_page_tolerates_an_unknown_session(self):
        page = self.client.get(
            reverse("checkout:complete"), {"session_id": "cs_test_missing"}
        )

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "We are confirming your payment.")

    @override_settings(
        **STRIPE_TEST_SETTINGS,
        EMAIL_HOST="smtp.example.com",
        DEFAULT_FROM_EMAIL="GrannyCoded <orders@example.com>",
        ORDER_NOTIFICATION_EMAIL="leah@example.com",
    )
    def test_paid_order_emails_the_customer_and_the_owner(self):
        product = self.create_product(stock=1)
        session = self.make_session(product)

        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self._post(self._event(session)).status_code, 200)

        session.refresh_from_db()
        self.assertEqual(len(mail.outbox), 2)
        customer, owner = mail.outbox

        self.assertEqual(customer.to, ["shopper@example.com"])
        self.assertIn(session.order_number, customer.subject)
        self.assertIn("12 Quilt Lane", customer.body)
        self.assertIn("$179.00", customer.body)
        self.assertIn("3 business days", customer.body)

        self.assertEqual(owner.to, ["leah@example.com"])
        self.assertIn(session.order_number, owner.subject)
        self.assertIn("Ship to", owner.body)
        self.assertIn("12 Quilt Lane", owner.body)
        self.assertIn("/dashboard/orders/", owner.body)
        self.assertIn("pi_test_1", owner.body)

    @override_settings(
        **STRIPE_TEST_SETTINGS,
        EMAIL_HOST="smtp.example.com",
        DEFAULT_FROM_EMAIL="GrannyCoded <orders@example.com>",
        ORDER_NOTIFICATION_EMAIL="leah@example.com",
    )
    def test_mail_failure_leaves_the_order_intact(self):
        product = self.create_product(stock=1)
        session = self.make_session(product)

        with patch(
            "home.services.order_notifications.send_mail",
            side_effect=SMTPException("relay down"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self._post(self._event(session))

        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.status, CheckoutSession.Status.PAID)
        self.assertTrue(session.order_number)
        Order = get_model("order", "Order")
        self.assertEqual(Order.objects.count(), 1)


class AddToCartCtaTests(CheckoutTestBase):
    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_product_page_offers_a_direct_checkout_button(self):
        product = self.create_product()

        page = self.client.get(product.get_absolute_url())

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Add to cart")
        self.assertContains(page, "Buy it now")
        self.assertContains(page, 'value="/checkout/"', html=False)

    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_buy_it_now_lands_on_the_checkout_page(self):
        product = self.create_product()

        response = self.client.post(
            reverse("basket:add", kwargs={"pk": product.pk}),
            {"quantity": 1, "next": reverse("checkout:index")},
        )

        self.assertRedirects(response, reverse("checkout:index"))
        page = self.client.get(reverse("checkout:index"))
        self.assertContains(page, "Mimi Quilt Coat")

    @override_settings(**STRIPE_TEST_SETTINGS)
    def test_cart_flash_offers_a_checkout_button(self):
        product = self.create_product()

        response = self.client.post(
            reverse("basket:add", kwargs={"pk": product.pk}),
            {"quantity": 1, "next": product.get_absolute_url()},
        )
        page = self.client.get(response.headers["Location"])

        self.assertContains(page, 'class="primary-action flash-checkout"', html=False)
        self.assertContains(page, ">Checkout<", html=False)
