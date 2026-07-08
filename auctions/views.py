from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from auctions.models import AuctionLot, BidLog
from auctions.scheduler import reschedule_lot_closing
import logging

logger = logging.getLogger(__name__)


class WhatsAppWebhookView(APIView):
    """مستقبل الـ Webhook الخاص بـ Meta WhatsApp Cloud API"""

    def get(self, request):
        """خطوة التحقق الإلزامية (Verification) التي يطلبها فيسبوك عند ربط الـ Webhook لأول مرة"""
        verify_token = "YOUR_SECRET_TOKEN"  # الرمز الذي ستضعه في إعدادات Meta
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == verify_token:
                return Response(int(challenge), status=status.HTTP_200_OK)
        return Response("Forbidden", status=status.HTTP_403_FORBIDDEN)

    def post(self, request):
        """استقبال رسائل المزايدات الحية من جروب الواتساب وتحديث المزاد فوراً"""
        data = request.data

        try:
            # 1. دعم النمط المباشر البسيط (للاختبارات التجريبية والـ Load Testing)
            if "bid_amount" in data or "text" in data:
                bidder_whatsapp = data.get("wa_id", "96777000000")
                bidder_name = data.get("name", "Anonymous")
                message_body = str(
                    data.get("bid_amount") or data.get("text", "")
                ).strip()

            # النمط الرسمي الخاص بـ Meta WhatsApp Cloud API
            else:
                entry = data.get("entry", [{}])[0]
                changes = entry.get("changes", [{}])[0]
                value = changes.get("value", {})
                messages = value.get("messages", [])

                if not messages:
                    return Response({"status": "ignored"}, status=status.HTTP_200_OK)

                message = messages[0]
                bidder_whatsapp = message.get("from")
                bidder_name = (
                    value.get("contacts", [{}])[0]
                    .get("profile", {})
                    .get("name", "Anonymous")
                )
                message_body = message.get("text", {}).get("body", "").strip()

            # 2. تحويل النص إلى رقم عشري
            try:
                bid_amount = Decimal(message_body)
            except (ValueError, InvalidOperation):
                return Response(
                    {"status": "not a valid bid"}, status=status.HTTP_200_OK
                )

            # 3. معالجة المزايدة بداخل عملة ذرية مقفلة (Row Locking) لمنع الـ Race Conditions
            with transaction.atomic():
                # جلب اللوت النشط حالياً وقفل السجل لحين انتهاء هذا الطلب
                lot = (
                    AuctionLot.objects.select_for_update()
                    .filter(
                        is_closed=False,
                        start_time__lte=timezone.now(),
                        end_time__gte=timezone.now(),
                    )
                    .first()
                )

                if not lot:
                    return Response(
                        {"error": "No active auction lot found"},
                        status=status.HTTP_200_OK,
                    )

                # التحقق من أن السعر الجديد أعلى من السعر الحالي
                if bid_amount > lot.current_highest_bid:
                    lot.current_highest_bid = bid_amount
                    lot.highest_bidder_whatsapp = bidder_whatsapp
                    lot.highest_bidder_name = bidder_name

                    # 💡 حل شرط العميل: تمديد وقت المزاد 10 ثوانٍ إضافية من اللحظة الحالية أو وقت النهاية
                    lot.end_time = timezone.now() + timedelta(seconds=10)
                    lot.save()

                    # تسجيل المزايدة في السجل التاريخي لقاعدة البيانات
                    BidLog.objects.create(
                        lot=lot,
                        bidder_whatsapp=bidder_whatsapp,
                        bidder_name=bidder_name,
                        bid_amount=bid_amount,
                    )

                    # تحديث المؤقت بالخلفية وإعادة الجدولة للوقت الجديد
                    reschedule_lot_closing(lot.id, lot.end_time)

                    logger.info(
                        f"✅ Bid accepted: {bid_amount} by {bidder_name}. New End Time: {lot.end_time}"
                    )

                    # (هنا يمكنك إرسال رسالة تأكيد فورا عبر الـ API للجروب: "أنت المزايد الأعلى الآن")
                    return Response(
                        {"status": "bid_accepted"}, status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {"status": "bid_too_low"}, status=status.HTTP_200_OK
                    )

        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            # العميل طلب: Error logs handled gracefully (no silent failures)
            return Response(
                {"status": "error", "message": str(e)}, status=status.HTTP_200_OK
            )
