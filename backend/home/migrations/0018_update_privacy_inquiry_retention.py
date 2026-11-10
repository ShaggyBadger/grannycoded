from django.db import migrations


PRIVACY_BODY = """<h2>Information we collect</h2>
<p>When you submit a custom-order request, we collect the name and email address you provide, your request details, and any optional reference photo you upload. Staff may add quote details, private notes, and an order record if you accept a custom quote. Staff may also record customer details for an in-person sale when needed for a receipt or follow-up.</p>
<h2>How we use it</h2>
<p>We use this information to review and respond to requests, prepare quotes, manage accepted work and sales, contact you about an order, and protect and operate the website.</p>
<h2>Reference photos and private records</h2>
<p>Customer reference photos are stored privately and are available only to authorized GrannyCoded staff. They are not published as product or editorial images. When an inquiry is deleted, its reference images are queued for removal after a 30-day recovery period.</p>
<p>We delete inquiries that have not become accepted orders after 12 months without activity. Accepted or converted inquiries may be retained as needed to manage an order, provide customer service, and meet applicable business, tax, or legal record-keeping requirements. You may contact us to ask about, correct, or request deletion of information you submitted. We may need to retain information for an active order or other record-keeping obligation.</p>
<h2>Service providers and email</h2>
<p>We use service providers to host the website and database, store uploaded files, and deliver email. They process information as needed to provide those services. If email notifications for new inquiries are configured, the inquiry details may be sent through our email provider to a designated GrannyCoded inbox. We do not sell personal information or use it for targeted advertising.</p>
<h2>Cookies and site operation</h2>
<p>The site uses necessary session and security cookies to support features such as the shopping basket and form protection. The public site does not currently include third-party advertising trackers or analytics scripts.</p>
<h2>Payments</h2>
<p>Online checkout is currently disabled, and this site does not collect payment-card details. Before online payments are enabled, we will update this notice to explain the information involved and identify the payment provider.</p>
<h2>Your choices and questions</h2>
<p>Contact us at <a href="mailto:grannycoded@gmail.com">grannycoded@gmail.com</a> with questions or requests about your information. Rights and exceptions depend on applicable law; we may retain information needed to fulfill an order or meet record-keeping obligations.</p>
<p>Last updated November 10, 2026.</p>"""


def update_privacy_notice(apps, schema_editor):
    PolicyPage = apps.get_model("home", "PolicyPage")
    PolicyPage.objects.using(schema_editor.connection.alias).filter(
        slug="privacy",
        body__contains="Inquiry records do not currently expire automatically.",
    ).update(body=PRIVACY_BODY)


class Migration(migrations.Migration):
    dependencies = [
        ("home", "0017_alter_checkoutsession_stripe_session_id"),
    ]

    operations = [
        migrations.RunPython(update_privacy_notice, migrations.RunPython.noop),
    ]
