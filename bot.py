import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

CITY, DELIVERY, PRODUCT = range(3)
user_data = {}

cities = ["Харьков", "Одесса", "Днепр", "Львов", "Запорожье", "Винница", "Херсон"]
deliveries = {"taxi": "🚕 Такси", "nova": "📦 Новая Почта", "klad": "🗺️ Клад"}
products = {
    "weed1": {"name": "🍁 Гашиш (1г)", "price": 500},
    "weed5": {"name": "🍁 Гашиш (5г)", "price": 2000},
    "coke1": {"name": "❄️ Кокаин (1г)", "price": 2500},
    "mdma1": {"name": "💊 MDMA (1шт)", "price": 800},
    "lsd1": {"name": "🌈 LSD (1шт)", "price": 1000},
    "meth1": {"name": "⚗️ Метамфетамин (1г)", "price": 1800}
}

async def start(update: Update, context):
    user_id = update.effective_user.id
    user_data[user_id] = {"cart": []}
    keyboard = [[InlineKeyboardButton(city, callback_data=f"city_{city}")] for city in cities]
    await update.message.reply_text("🌍 ВЫБЕРИТЕ ГОРОД:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CITY

async def city_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    city = query.data.replace("city_", "")
    user_data[user_id]["city"] = city
    
    keyboard = [
        [InlineKeyboardButton("🚕 Такси", callback_data="del_taxi")],
        [InlineKeyboardButton("📦 Новая Почта", callback_data="del_nova")],
        [InlineKeyboardButton("🗺️ Клад", callback_data="del_klad")]
    ]
    await query.edit_message_text(f"📍 Город: {city}\n\n🚚 ВЫБЕРИТЕ ДОСТАВКУ:", reply_markup=InlineKeyboardMarkup(keyboard))
    return DELIVERY

async def delivery_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    delivery_key = query.data.replace("del_", "")
    user_data[user_id]["delivery"] = deliveries[delivery_key]
    
    keyboard = []
    for prod_id, prod_info in products.items():
        btn_text = f"{prod_info['name']} - {prod_info['price']} грн"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"prod_{prod_id}")])
    
    keyboard.append([InlineKeyboardButton("🛒 ПОСМОТРЕТЬ КОРЗИНУ", callback_data="view_cart")])
    keyboard.append([InlineKeyboardButton("✅ ЗАВЕРШИТЬ ВЫБОР", callback_data="finish")])
    keyboard.append([InlineKeyboardButton("❌ ОТМЕНИТЬ", callback_data="cancel")])
    
    await query.edit_message_text(f"🚚 Доставка: {deliveries[delivery_key]}\n\n🛒 ВЫБЕРИТЕ ТОВАР:", reply_markup=InlineKeyboardMarkup(keyboard))
    return PRODUCT

async def product_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = {"cart": []}
    
    data = query.data
    
    if data == "view_cart":
        cart = user_data[user_id].get("cart", [])
        if not cart:
            await query.answer("🛒 Корзина пуста! Добавьте товары.", show_alert=True)
        else:
            cart_text = "🛒 ВАША КОРЗИНА:\n\n"
            total = 0
            for item in cart:
                cart_text += f"• {item['name']} - {item['price']} грн\n"
                total += item['price']
            cart_text += f"\n💰 ИТОГО: {total} грн"
            await query.answer(cart_text, show_alert=True)
        return PRODUCT
    
    elif data.startswith("prod_"):
        prod_id = data.replace("prod_", "")
        if prod_id in products:
            product = products[prod_id]
            user_data[user_id]["cart"].append({"name": product["name"], "price": product["price"]})
            await query.answer(f"✅ Добавлено: {product['name']}", show_alert=True)
        return PRODUCT
    
    elif data == "finish":
        cart = user_data[user_id].get("cart", [])
        if not cart:
            await query.answer("❌ Корзина пуста! Добавьте товары.", show_alert=True)
            return PRODUCT
        
        order_text = "✅ ЗАКАЗ ОФОРМЛЕН\n\n"
        order_text += f"📍 Город: {user_data[user_id].get('city', '—')}\n"
        order_text += f"🚚 Доставка: {user_data[user_id].get('delivery', '—')}\n\n"
        order_text += "📦 ТОВАРЫ:\n"
        
        total = 0
        for item in cart:
            order_text += f"• {item['name']} - {item['price']} грн\n"
            total += item['price']
        
        order_text += f"\n💰 СУММА ЗАКАЗА: {total} грн\n"
        order_text += "⏰ Срок доставки: 30-90 минут\n\n"
        order_text += "📞 ДЛЯ ОПЛАТЫ И ПОДТВЕРЖДЕНИЯ:\n"
        order_text += "Свяжитесь с оператором: @kldukr_mng\n\n"
        order_text += "🔐 ИНСТРУКЦИЯ ПО БЕЗОПАСНОСТИ:\n"
        order_text += "1. Только личные сообщения с оператором\n"
        order_text += "2. Не обсуждайте детали в общем чате\n"
        order_text += "3. Используйте шифрование\n"
        order_text += "4. Оплата криптовалютой\n\n"
        order_text += "🔄 Для нового заказа: /start"
        
        await query.edit_message_text(order_text)
        user_data[user_id]["cart"] = []
        return ConversationHandler.END
    
    elif data == "cancel":
        user_data[user_id] = {"cart": []}
        await query.edit_message_text("❌ Заказ отменен.\n\nДля нового заказа используйте /start")
        return ConversationHandler.END
    
    return PRODUCT

async def cancel_command(update: Update, context):
    user_id = update.effective_user.id
    user_data[user_id] = {"cart": []}
    await update.message.reply_text("❌ Заказ отменен.\n\n/start — новый заказ")
    return ConversationHandler.END

async def help_command(update: Update, context):
    await update.message.reply_text(
        "📖 КОМАНДЫ:\n\n"
        "/start — начать заказ\n"
        "/cancel — отменить заказ\n"
        "/help — помощь\n\n"
        "👤 ОПЕРАТОР: @kldukr_mng\n\n"
        "📍 Города: Харьков, Одесса, Днепр, Львов, Запорожье, Винница, Херсон\n"
        "🚚 Доставка: Такси, Новая Почта, Клад"
    )

def main():
    TOKEN = "7461220596:AAHmvyDgPs87JTYGGnLpB2OxTxTKFGCuUbQ"
    
    app = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CITY: [CallbackQueryHandler(city_handler, pattern='^city_')],
            DELIVERY: [CallbackQueryHandler(delivery_handler, pattern='^del_')],
            PRODUCT: [CallbackQueryHandler(product_handler, pattern='^(prod_|view_cart|finish|cancel)$')]
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('help', help_command))
    
    print("=" * 50)
    print("🤖 ТЕЛЕГРАМ БОТ ЗАПУЩЕН")
    print(f"📍 {len(cities)} городов")
    print(f"🛒 {len(products)} товаров")
    print(f"👤 Оператор: @kldukr_mng")
    print(f"🚚 Способы доставки: Такси, НП, Клад")
    print("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == '__main__':
    main()
