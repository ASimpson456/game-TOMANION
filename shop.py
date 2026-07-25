# товары магазина

ITEM_PRICE = 500

SHOP_ITEMS = [
    {
        "id": "tomato_hat",
        "hero": "tomato",
        "name": "Шляпа",
        "desc": "Шляпа для Томата",
    },
    {
        "id": "tomato_sword",
        "hero": "tomato",
        "name": "Меч",
        "desc": "Меч (просто красивый)",
    },
    {
        "id": "onion_hat",
        "hero": "onion",
        "name": "Шляпа",
        "desc": "Шляпа для Лука",
    },
    {
        "id": "onion_bow",
        "hero": "onion",
        "name": "Лук",
        "desc": "Лук на спину (не стреляет)",
    },
]


def item_by_id(item_id):
    for item in SHOP_ITEMS:
        if item["id"] == item_id:
            return item
    return None
