"""Capture the privacy notice as edited on the live site.

The live page was rewritten in the Wagtail admin during launch and no longer
matched the text shipped by migrations 0015 and 0018: payments and Stripe are
described, records no longer claim automatic expiry, and Analytics is disclosed.
This records that copy in the repository and adds the sentence the live text was
missing about Analytics user-provided data.
"""

from django.db import migrations
from django.db.models import Q


PRIVACY_INTRO = (
    "This notice explains what GrannyCoded collects when you send a custom-work "
    "request or place an order, how it is used, and who handles it."
)

PRIVACY_BODY = """<h2>Information we collect</h2>
<p>When you send a custom-work request, we collect the name and email address you provide, your request details, and any optional reference photo you upload.</p>
<p>When you place an online order, we collect your name, email address, shipping address, and the items and total you ordered. Staff may also record customer details for an in-person sale when needed for a receipt or follow-up.</p>
<p>Staff may add quote details, private notes, and an order record if you accept a custom quote.</p>
<h2>How we use it</h2>
<p>We use this information to review and respond to requests, prepare quotes, manage orders and sales, ship your order, contact you about it, and protect and operate the website.</p>
<h2>Payments</h2>
<p>Online payments are processed by Stripe, a payment provider. When you pay, you enter your card details on Stripe's own payment page. GrannyCoded never receives, sees, or stores your full card number or the security code on the card.</p>
<p>We receive confirmation that a payment succeeded, the amount, and a reference we use to match that payment to your order. Refunds are sent back to your card through Stripe. Stripe's own privacy policy explains how it handles payment information.</p>
<h2>Reference photos and private records</h2>
<p>Customer reference photos are stored privately and are available only to authorized GrannyCoded staff. They are not published as product or editorial images. If an inquiry is deleted, its reference images are marked for deletion with a 30-day recovery period before storage cleanup.</p>
<p>Inquiry and order records do not currently expire automatically. Staff retain them for as long as they are useful for reviewing requests, managing work, customer service, and necessary business records. You may contact us to request deletion; we may need to keep some information for an active order or another record-keeping obligation.</p>
<h2>Service providers and email</h2>
<p>We use service providers to host the website and database, store uploaded files, process payments, and deliver email. They process information as needed to provide those services. Order confirmations and new-order notifications pass through our email provider. We do not sell personal information or use it for targeted advertising.</p>
<h2>Cookies and site operation</h2>
<p>The site uses necessary session and security cookies to support features such as the shopping basket and form protection.</p>
<p>We also use Google Analytics, loaded through Google Tag Manager, to see which pages and products people visit and which do not get looked at. That information is aggregated for us; it is not used for advertising, and we do not sell it. Analytics scripts are not loaded on the basket, checkout, or staff pages.</p>
<p>Analytics records the pages you view, the site or search that referred you, your approximate location, and your device and browser type. If you type an email address or phone number into a form on the site, Google may receive a hashed copy so a visit can be tied to a request; we do not use it to contact you or for advertising.</p>
<p>You can block analytics with a browser setting or an extension such as an ad blocker; the shop will keep working.</p>
<h2>Your choices and questions</h2>
<p>You may contact us to ask about, correct, or request deletion of information you submitted. Rights and exceptions depend on applicable law; we may keep information needed to fulfill an order or meet record-keeping obligations.</p>
<p>Last updated November 12, 2026.</p>"""

# Only the captured notice carries this sentence, so the update runs once.
CAPTURED_MARKER = "Google may receive a hashed copy"


def capture_live_privacy_notice(apps, schema_editor):
    """Replace pre-launch privacy copy with the notice edited on the live site.

    Pages already carrying the captured text, or carrying a body the site never
    shipped, are left alone so an administrator's revision is not overwritten.
    """
    PolicyPage = apps.get_model("home", "PolicyPage")
    PolicyPage.objects.using(schema_editor.connection.alias).filter(
        slug="privacy"
    ).filter(
        Q(body__contains="does not currently include third-party advertising trackers")
        | Q(body__contains="We also use Google Analytics")
    ).exclude(
        body__contains=CAPTURED_MARKER
    ).update(
        body=PRIVACY_BODY,
        intro=PRIVACY_INTRO,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0019_checkoutsession_basket_id"),
    ]

    operations = [
        migrations.RunPython(capture_live_privacy_notice, migrations.RunPython.noop),
    ]
