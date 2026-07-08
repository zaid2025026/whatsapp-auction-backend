from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# إنشاء نسخة واحدة من الجدولة للعمل في الخلفية
scheduler = BackgroundScheduler()
scheduler.start()


def announce_winner_task(lot_id):
    """هذه المهمة تنطلق تلقائياً فور انتهاء وقت المزاد لإغلاقه وإعلان الفائز"""
    from auctions.models import AuctionLot
    from django.db import transaction

    # قفل السجل لضمان عدم حدوث تغيير أثناء الإغلاق
    with transaction.atomic():
        try:
            lot = AuctionLot.objects.select_for_update().get(id=lot_id, is_closed=False)

            # التحقق الفعلي من الوقت للتأكد من عدم وجود تمديد أخير
            if timezone.now() >= lot.end_time:
                lot.is_closed = True
                lot.save()

                logger.info(
                    f"🚨 LOT {lot.id} CLOSED! Winner: {lot.highest_bidder_whatsapp} with {lot.current_highest_bid} AUD"
                )

                # 📞 هنا يتم استدعاء دالة لإرسال رسالة للمجموعة خاص بالواتساب بالإغلاق وبيانات الدفع
                # send_whatsapp_message(lot.highest_bidder_whatsapp, f"تهانينا! لقد فزت بـ {lot.title}..")
            else:
                # إذا تمدد الوقت، نعيد جدولة المهمة للوقت الجديد
                reschedule_lot_closing(lot.id, lot.end_time)
        except AuctionLot.DoesNotExist:
            pass


def reschedule_lot_closing(lot_id, new_end_time):
    """إلغاء مهمة الإغلاق السابقة وجدولة مهمة جديدة بالوقت المحدث (+10 ثوانٍ)"""
    job_id = f"close_lot_{lot_id}"

    # إزالة المهمة القديمة إن وجدت
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    # إضافة المهمة بالوقت الجديد
    scheduler.add_job(
        announce_winner_task,
        "date",
        run_date=new_end_time,
        args=[lot_id],
        id=job_id,
        replace_existing=True,
    )
    logger.info(f"🔄 Rescheduled Lot {lot_id} to close at {new_end_time}")
