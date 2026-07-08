from django.urls import path
from auctions.views import WhatsAppWebhookView

urlpatterns = [
    path("webhook/", WhatsAppWebhookView.as_view(), name="whatsapp_webhook"),
]
