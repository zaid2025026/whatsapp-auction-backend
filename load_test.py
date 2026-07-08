import threading
import requests
import json
import time

# رابط الـ Webhook المحلي للمشروع
WEBHOOK_URL = "http://127.0.0.1:8000/api/v1/whatsapp/webhook/"


def send_simultaneous_bid(bidder_number, bid_value):
    """محاكاة إرسال طلب مزايدة منفصل تماماً من هاتف واتساب مختلف وفي نفس اللحظة"""
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "contacts": [
                                {"profile": {"name": f"Bidder_{bidder_number}"}}
                            ],
                            "messages": [
                                {
                                    "from": f"966500000{bidder_number:03d}",
                                    "text": {"body": str(bid_value)},
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }

    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(WEBHOOK_URL, data=json.dumps(payload), headers=headers)
        print(
            f"👤 Bidder {bidder_number} placed {bid_value} AUD -> Status Code: {response.status_code} | Response: {response.json()}"
        )
    except Exception as e:
        print(f"❌ Error for Bidder {bidder_number}: {e}")


if __name__ == "__main__":
    print("🔥 Starting High-Concurrency Load Test (Simulated WhatsApp Bids)...")
    threads = []

    start_time = time.time()

    # محاكاة دخول 500 طلب متزامن دفعة واحدة
    base_bid = 500
    for i in range(1, 501):
        # زيادة تصاعدية طفيفة لمحاكاة تنافس الأسعار الحقيقي
        current_bid = base_bid + i

        t = threading.Thread(target=send_simultaneous_bid, args=(i, current_bid))
        threads.append(t)
        t.start()

    # الانتظار حتى تنتهي كافة الخيوط (Threads) من إرسال طلباتها
    for t in threads:
        t.join()

    duration = time.time() - start_time
    print(
        f"\n✅ Load test completed successfully! 500 concurrent bids processed in {duration:.2f} seconds."
    )
