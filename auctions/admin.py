from django.contrib import admin
from auctions.models import AuctionLot, BidLog


class BidLogInline(admin.TabularInline):
    """تسمح برؤية سجل المزايدات الخاص بكل لوت مباشرة من داخل صفحة اللوت نفسه"""

    model = BidLog
    extra = 0
    readonly_fields = ("bidder_whatsapp", "bidder_name", "bid_amount", "timestamp")
    can_delete = False


@admin.register(AuctionLot)
class AuctionLotAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "starting_price",
        "current_highest_bid",
        "highest_bidder_name",
        "end_time",
        "is_closed",
    )
    list_filter = ("is_closed", "start_time", "end_time")
    search_fields = ("title", "highest_bidder_whatsapp", "highest_bidder_name")
    readonly_fields = (
        "current_highest_bid",
        "highest_bidder_whatsapp",
        "highest_bidder_name",
    )
    inlines = [BidLogInline]


@admin.register(BidLog)
class BidLogAdmin(admin.ModelAdmin):
    list_display = ("lot", "bidder_name", "bidder_whatsapp", "bid_amount", "timestamp")
    list_filter = ("timestamp",)
    search_fields = ("bidder_whatsapp", "bidder_name", "lot__title")
