from django.urls import path

from home import checkout_views
from home.views import checkout_unavailable

app_name = "checkout"

urlpatterns = [
    path("", checkout_views.payment_summary, name="index"),
    path("start/", checkout_views.start_checkout, name="start"),
    path("complete/", checkout_views.complete, name="complete"),
    path("webhook/", checkout_views.webhook, name="webhook"),
    path("payment-security/", checkout_views.payment_security, name="payment_security"),
    path("<path:step>/", checkout_unavailable, name="disabled_step"),
]
