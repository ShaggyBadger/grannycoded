"""Create Oscar order records for in-person sales and accepted custom quotes."""

from collections.abc import Iterable
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from oscar.apps.shipping.methods import FixedPrice, NoShippingRequired
from oscar.core.loading import get_class, get_model


class InventoryUnavailable(ValidationError):
    """Raised when an order exceeds the currently available stock."""


class InPersonCollection(NoShippingRequired):
    code = "in-person-collection"
    name = "In-person collection"


@transaction.atomic
def create_oscar_order(
    request,
    line_items: Iterable[tuple[object, int]],
    *,
    customer_email: str = "",
    shipping_amount: Decimal = Decimal("0.00"),
    note: str = "",
    payment_method: str = "",
    collect_in_person: bool = False,
    shipping_address=None,
):
    """Place an order, reserve its stock, and optionally record a completed sale."""
    Basket = get_model("basket", "Basket")
    Product = get_model("catalogue", "Product")
    StockRecord = get_model("partner", "StockRecord")
    Partner = get_model("partner", "Partner")
    OrderNote = get_model("order", "OrderNote")
    PaymentEventType = get_model("order", "PaymentEventType")
    ShippingEventType = get_model("order", "ShippingEventType")
    OrderCreator = get_class("order.utils", "OrderCreator")
    OrderTotalCalculator = get_class("checkout.calculators", "OrderTotalCalculator")
    EventHandler = get_class("order.processing", "EventHandler")

    quantities: dict[int, int] = {}
    product_by_id = {}
    for product, quantity in line_items:
        if quantity < 1:
            raise ValidationError("Each order line must have a positive quantity.")
        product_by_id[product.pk] = product
        quantities[product.pk] = quantities.get(product.pk, 0) + quantity
    if not quantities:
        raise ValidationError("An order must contain at least one item.")

    partner = Partner.objects.get(code="grannycoded")
    stockrecords = list(
        StockRecord.objects.select_for_update()
        .filter(product_id__in=quantities, partner=partner)
        .order_by("pk")
    )
    stockrecord_by_product = {record.product_id: record for record in stockrecords}
    if len(stockrecord_by_product) != len(quantities):
        raise InventoryUnavailable("One or more items have no GrannyCoded stock record.")

    for product_id, quantity in quantities.items():
        stockrecord = stockrecord_by_product[product_id]
        available = (stockrecord.num_in_stock or 0) - (stockrecord.num_allocated or 0)
        if quantity > available:
            title = product_by_id[product_id].get_title()
            raise InventoryUnavailable(
                f"{title} has {max(available, 0)} available; {quantity} requested."
            )

    basket = Basket.objects.create()
    basket.strategy = request.strategy
    for product_id, quantity in quantities.items():
        basket.add_product(product_by_id[product_id], quantity)

    if collect_in_person:
        shipping_method = InPersonCollection()
    else:
        shipping_method = FixedPrice(
            charge_excl_tax=shipping_amount,
            charge_incl_tax=shipping_amount,
        )
    shipping_charge = shipping_method.calculate(basket)
    total = OrderTotalCalculator().calculate(basket, shipping_charge)
    if shipping_address is not None and shipping_address.pk is None:
        # Oscar's order model needs a saved address to point at.
        shipping_address.save()
    order = OrderCreator().place_order(
        basket=basket,
        total=total,
        shipping_method=shipping_method,
        shipping_charge=shipping_charge,
        request=request,
        guest_email=customer_email,
        shipping_address=shipping_address,
    )

    basket.status = Basket.SUBMITTED
    basket.date_submitted = timezone.now()
    basket.save(update_fields=["status", "date_submitted"])

    if note:
        OrderNote.objects.create(
            order=order,
            user=request.user if request.user.is_authenticated else None,
            note_type=OrderNote.INFO,
            message=note,
        )

    if payment_method:
        lines = list(order.lines.all())
        quantities_by_line = [line.quantity for line in lines]
        payment_type = PaymentEventType.objects.get(code="paid")
        handler = EventHandler(user=request.user)
        handler.handle_payment_event(
            order,
            payment_type,
            amount=order.total_incl_tax,
            lines=lines,
            line_quantities=quantities_by_line,
            reference=f"In-person payment: {payment_method}",
        )
        if collect_in_person:
            collected_type = ShippingEventType.objects.get(code="collected")
            handler.handle_shipping_event(
                order,
                collected_type,
                lines,
                quantities_by_line,
                reference="Collected in person",
            )
            for line in lines:
                line.consume_allocation(line.quantity)
            order.set_status("Being processed")
            order.set_status("Complete")

    return order


@transaction.atomic
def create_order_for_custom_inquiry(request, inquiry):
    """Create a private one-off Oscar product and pending order from an accepted quote."""
    if inquiry.order_id:
        return inquiry.order
    if inquiry.status != inquiry.Status.ACCEPTED or inquiry.quoted_total is None:
        raise ValidationError("Accept and price the quote before creating an order.")

    shipping_amount = inquiry.quoted_shipping or Decimal("0.00")
    product_amount = inquiry.quoted_total - shipping_amount
    if product_amount <= Decimal("0.00"):
        raise ValidationError("The quoted item amount must be greater than zero.")

    Product = get_model("catalogue", "Product")
    ProductClass = get_model("catalogue", "ProductClass")
    ProductCategory = get_model("catalogue", "ProductCategory")
    Category = get_model("catalogue", "Category")
    StockRecord = get_model("partner", "StockRecord")
    Partner = get_model("partner", "Partner")
    ProductAttribute = get_model("catalogue", "ProductAttribute")
    ProductAttributeValue = get_model("catalogue", "ProductAttributeValue")

    product_class = ProductClass.objects.get(slug="handmade-goods")
    partner = Partner.objects.get(code="grannycoded")
    category = Category.objects.get(slug="other-handmade-goods")
    product_slug = f"custom-order-{inquiry.pk}"
    product = Product.objects.create(
        structure=Product.STANDALONE,
        is_public=False,
        title=f"Custom order #{inquiry.pk} for {inquiry.name}",
        slug=product_slug,
        description=inquiry.request_details,
        product_class=product_class,
    )
    ProductCategory.objects.create(product=product, category=category)
    StockRecord.objects.create(
        product=product,
        partner=partner,
        partner_sku=product_slug,
        price_currency="USD",
        price=product_amount,
        num_in_stock=1,
        num_allocated=0,
    )
    one_of_a_kind = ProductAttribute.objects.filter(
        product_class=product_class,
        code="one_of_a_kind",
    ).first()
    if one_of_a_kind:
        ProductAttributeValue.objects.create(
            product=product,
            attribute=one_of_a_kind,
            value_boolean=True,
        )

    details = f"Custom order inquiry #{inquiry.pk}: {inquiry.request_details}"
    if inquiry.shipping_note:
        details += f"\nShipping: {inquiry.shipping_note}"
    order = create_oscar_order(
        request,
        [(product, 1)],
        customer_email=inquiry.email,
        shipping_amount=shipping_amount,
        note=details,
    )
    inquiry.order = order
    inquiry.status = inquiry.Status.CONVERTED
    inquiry.save(update_fields=["order", "status", "updated_at"])
    return order
