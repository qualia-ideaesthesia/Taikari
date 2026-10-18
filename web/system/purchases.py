"""Purchase catalog operations for the web admin UI."""

import time

from core.sql import Connect


def get_all_purchase():
    with Connect() as c:
        c.execute("""select * from purchase""")
        x = c.fetchall()

        # Fetch every purchase item in a single query instead of one query per
        # purchase (avoids an N+1 pattern).
        c.execute(
            """select purchase_name, item_id, type, amount from purchase_item"""
        )
        items_by_purchase = {}
        for j in c.fetchall():
            items_by_purchase.setdefault(j[0], []).append(
                {"item_id": j[1], "type": j[2], "amount": j[3]}
            )

        re = []
        for i in x:

            discount_from = None
            discount_to = None
            discount_reason = "Yes" if i[5] == "anni5tix" else "No"

            if i[3] and i[3] >= 0:
                discount_from = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(int(i[3]) / 1000)
                )
            if i[4] and i[4] >= 0:
                discount_to = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(int(i[4]) // 1000)
                )

            re.append(
                {
                    "purchase_name": i[0],
                    "price": i[1],
                    "orig_price": i[2],
                    "discount_from": discount_from,
                    "discount_to": discount_to,
                    "discount_reason": discount_reason,
                    "items": items_by_purchase.get(i[0], []),
                }
            )

    return re
