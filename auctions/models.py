from django.db import models
from django.utils import timezone
from decimal import Decimal


class AuctionLot(models.Model):
    """يمثل الصنف أو اللوت المعروض للمزاد حالياً في مجموعة الواتساب"""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    starting_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # تفاصيل المزايدة الحالية (يتم تحديثها ديناميكياً)
    current_highest_bid = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00
    )
    highest_bidder_whatsapp = models.CharField(
        max_length=20, blank=True, null=True, db_index=True
    )
    highest_bidder_name = models.CharField(max_length=255, blank=True, null=True)

    # توقيت التحكم بالمزاد
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(
        db_index=True
    )  # التوقيت الذي سيمتد ديناميكياً 10 ثوانٍ

    is_closed = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Lot: {self.title} | High Bid: {self.current_highest_bid} AUD"


class BidLog(models.Model):
    """سجل تاريخي صارم لكافة المزايدات القادمة من الواتساب لمنع التلاعب وتسهيل التدقيق"""

    lot = models.ForeignKey(AuctionLot, on_delete=models.CASCADE, related_name="bids")
    bidder_whatsapp = models.CharField(max_length=20, db_index=True)
    bidder_name = models.CharField(max_length=255, blank=True, null=True)
    bid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-timestamp"]  # جلب المزايدات الأحدث أولاً دائماً

    def __str__(self):
        return f"{self.bidder_name or self.bidder_whatsapp} placed {self.bid_amount} on {self.lot.title}"
