# Checkout Friction: Double-Button, Below-the-Fold CTA

Status: **noted, not started.** No code has been changed. Captured from a real
purchase walkthrough on 12 Nov 2026.

## What the shopper experiences

1. Cart (`/basket/`) ends with a primary button: **Continue to checkout**
2. That goes to `/checkout/`, which shows the items again, then an **Order
   summary** panel, then a **Payment handled by Stripe** assurance block, and
   only then **Continue to secure payment**

Because the second primary button sits below the summary and assurance copy, on
a laptop viewport and on mobile it is below the fold. The shopper has already
pressed one full-width primary button and now has to scroll to find the next one.
It reads as "check in twice" and makes the step feel stalled.

## Why it happens

- `basket.html` and `checkout_payment.html` both use `.primary-action
  .checkout-action`, so two identical-weight calls to action appear in sequence
  with no visual hierarchy between them.
- In `checkout_payment.html` the `<form>` with the CTA is the last element of
  `.cart-summary`, after `.payment-assurance`.
- `.cart-layout` stacks on narrow viewports, so the summary — and the CTA with
  it — moves below the full item list.

## Options (not yet chosen)

1. **Move the CTA up.** Put the form directly after the `.cart-total` line,
   above the assurance block. Smallest change, fixes the fold on desktop.
2. **Sticky summary on mobile.** Keep totals and the CTA in a bar pinned to the
   bottom of the viewport on narrow screens.
3. **Make the step feel like payment, not a review.** Label the button with the
   amount — "Pay $80.00" — instead of "Continue to secure payment". The shopper
   then knows the next tap is the money.
4. **Differentiate the two steps.** Retitle the cart button to "Review order"
   and the checkout heading to "Pay", so it does not read as the same action
   twice.
5. **Skip the review step** for a single-line basket. Faster, but removes the
   shipping-included reassurance and the address the shopper is about to use;
   probably not worth it.

## Recommendation

Do options 1, 3, 4, and reorder the mobile layout. Specifically:

1. In `checkout_payment.html`, move the payment `<form>` block from the end of
   `.cart-summary` to directly after the `.cart-total` line, above
   `.payment-assurance`. Trust copy follows the button instead of blocking it.
2. Change the button label to include the amount:
   `Pay {{ total|currency:currency }}`. Add one line beneath it: "Card details
   are entered on Stripe's secure page."
3. Change the cart button in `basket.html` from "Continue to checkout" to
   "Review order", so the sequence reads review → pay rather than the same
   action twice.
4. In the narrow-viewport media query, add `order: -1` to `.cart-summary` so the
   totals and pay button appear before the item list on phones.

Keep the whole review step; it carries the shipping-included reassurance and the
address the shopper is about to use. The fix is hierarchy, not removing a step.

Not doing: skipping the review step (option 5) and a sticky mobile bar
(option 2). Revisit the sticky bar only if measurement shows the reordered
layout still loses people on phones.

## Verification when it is built

- 375 px and 1440 px: CTA visible without scrolling on first paint
- Keyboard: tab order reaches the CTA before the assurance text
- The form still POSTs to `checkout:start` and survives with JS disabled
- A test purchase still creates one order and one stock deduction
