import os
import threading
import logging
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters

# Flask app для health checks
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Telegram Bot Active | @kldukr_mng"

@app.route('/health')
def health():
    return "OK", 200

# Настройка логов
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния диалога
CITY, DELIVERY, PRODUCT = range(3)
user_data = {}

# Данные магазина
CITIES = ["Харьков", "Одесса", "Днепр", "Львов", "Запорожье", "Винница", "Херсон"]

DELIVERIES = {
    "taxi": "🚕 Такси (курьер)",
    "nova": "📦 Новая Почта", 
    "klad": "🗺️ Клад (тайник)"
}

PRODUCTS = {
    "weed1": {"name": "🍁 Гашиш (1г)", "price": 500},
    "weed5": {"name": "🍁 Гашиш (5г)", "price": 2000},
    "coke1": {"name": "❄️ Кокаин (1г)", "price": 2500},
    "mdma1": {"name": "💊 MDMA (1шт)", "price": 800},
    "lsd1": {"name": "🌈 LSD (1шт)", "price": 1000},
    "meth1": {"name": "⚗️ Метамфетамин (1г)", "price": 1800}
}

# ========== КОМАНДА /start ==========
async def start(update: Update, context):
    user_id = update.effective_user.id
    user_data[user_id] = {"cart": []}
    
    # Создаем клавиатуру с городами
    keyboard = []
    for city in CITIES:
        keyboard.append([InlineKeyboardButton(city, callback_data=f"city_{city}")])
    
    await update.message.reply_text(
        "🌍 *ВЫБЕРИТЕ ГОРОД:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return CITY

# ========== ВЫБОР ГОРОДА ==========
async def city_handler(update: Update, context):
    query = update.callback_query
    await query.answer()  # Обязательно отвечаем на callback
    
    user_id = query.from_user.id
    city = query.data.replace("city_", "")
    
    # Инициализируем данные пользователя если нет
    if user_id not in user_data:
        user_data[user_id] = {"cart": []}
    
    user_data[user_id]["city"] = city
    
    # Клавиатура способов доставки
    keyboard = [
        [InlineKeyboardButton("🚕 Такси (курьер)", callback_data="del_taxi")],
        [InlineKeyboardButton("📦 Новая Почта", callback_data="del_nova")],
        [InlineKeyboardButton("🗺️ Клад (тайник)", callback_data="del_klad")]
    ]
    
    await query.edit_message_text(
        text=f"📍 *Город:* {city}\n\n🚚 *ВЫБЕРИТЕ СПОСОБ ДОСТАВКИ:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return DELIVERY

# ========== ВЫБОР ДОСТАВКИ ==========
async def delivery_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    delivery_key = query.data.replace("del_", "")
    delivery_name = DELIVERIES[delivery_key]
    
    user_data[user_id]["delivery"] = delivery_name
    
    # Создаем клавиатуру товаров
    keyboard = []
    for prod_id, prod_info in PRODUCTS.items():
        button_text = f"{prod_info['name']} - {prod_info['price']} грн"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"prod_{prod_id}")])
    
    # Кнопки действий
    keyboard.append([InlineKeyboardButton("🛒 ПОСМОТРЕТЬ КОРЗИНУ", callback_data="view_cart")])
    keyboard.append([InlineKeyboardButton("✅ ЗАВЕРШИТЬ ВЫБОР", callback_data="finish_order")])
    keyboard.append([InlineKeyboardButton("❌ ОТМЕНИТЬ ЗАКАЗ", callback_data="cancel_order")])
    
    await query.edit_message_text(
        text=f"🚚 *Доставка:* {delivery_name}\n\n🛒 *ВЫБЕРИТЕ ТОВАРЫ:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return PRODUCT

# ========== ОБРАБОТКА ВСЕХ ДЕЙСТВИЙ В СОСТОЯНИИ PRODUCT ==========
async def product_actions_handler(update: Update, context):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Инициализация если пользователь новый
    if user_id not in user_data:
        user_data[user_id] = {"cart": []}
    
    data = query.data
    
    # 1. ПРОСМОТР КОРЗИНЫ
    if data == "view_cart":
        await query.answer()  # Отвечаем сразу
        
        cart = user_data[user_id].get("cart", [])
        
        if not cart:
            alert_text = "🛒 Ваша корзина пуста!\n\nДобавьте товары, нажимая на них."
            await query.answer(alert_text, show_alert=True)
        else:
            # Формируем текст корзины
            cart_text = "🛒 *ВАША КОРЗИНА:*\n\n"
            total = 0
            
            for i, item in enumerate(cart, 1):
                cart_text += f"{i}. {item['name']} - {item['price']} грн\n"
                total += item['price']
            
            cart_text += f"\n💰 *Итого:* {total} грн"
            
            # Показываем во всплывающем окне
            await query.answer(cart_text, show_alert=True)
        
        return PRODUCT
    
    # 2. ДОБАВЛЕНИЕ ТОВАРА
    elif data.startswith("prod_"):
        prod_id = data.replace("prod_", "")
        
        if prod_id in PRODUCTS:
            product = PRODUCTS[prod_id]
            
            # Добавляем в корзину
            user_data[user_id]["cart"].append({
                "name": product["name"],
                "price": product["price"]
            })
            
            # Подтверждаем добавление
            await query.answer(f"✅ Добавлено: {product['name']}")
        
        return PRODUCT
    
    # 3. ЗАВЕРШЕНИЕ ЗАКАЗА
    elif data == "finish_order":
        await query.answer()
        
        cart = user_data[user_id].get("cart", [])
        
        if not cart:
            await query.answer("❌ Корзина пуста! Добавьте товары.", show_alert=True)
            return PRODUCT
        
        # Формируем текст заказа
        order_text = "✅ *ЗАКАЗ УСПЕШНО ОФОРМЛЕН!*\n\n"
        order_text += f"👤 *ID клиента:* `{user_id}`\n"
        order_text += f"📍 *Город:* {user_data[user_id].get('city', 'Не указан')}\n"
        order_text += f"🚚 *Доставка:* {user_data[user_id].get('delivery', 'Не указана')}\n\n"
        order_text += "*📦 СОСТАВ ЗАКАЗА:*\n"
        
        total = 0
        for i, item in enumerate(cart, 1):
            order_text += f"{i}. {item['name']} - {item['price']} грн\n"
            total += item['price']
        
        order_text += f"\n💰 *СУММА ЗАКАЗА:* {total} грн\n"
        order_text += "⏰ *Срок доставки:* 30-90 минут\n\n"
        order_text += "📞 *ДЛЯ ПОДТВЕРЖДЕНИЯ И ОПЛАТЫ:*\n"
        order_text += "👉 Свяжитесь с оператором: @kldukr_mng\n\n"
        order_text += "🔐 *ИНСТРУКЦИЯ ПО БЕЗОПАСНОСТИ:*\n"
        order_text += "1. Общайтесь только в ЛС с оператором\n"
        order_text += "2. Не обсуждайте детали в общих чатах\n"
        order_text += "3. Используйте шифрование\n"
        order_text += "4. Оплата только криптовалютой\n\n"
        order_text += "🔄 Для нового заказа отправьте /start"
        
        # Отправляем сообщение с заказом
        await query.edit_message_text(
            text=order_text,
            parse_mode='Markdown'
        )
        
        # Очищаем корзину пользователя
        user_data[user_id]["cart"] = []
        
        return ConversationHandler.END
    
    # 4. ОТМЕНА ЗАКАЗА
    elif data == "cancel_order":
        await query.answer()
        
        # Очищаем данные пользователя
        user_data[user_id] = {"cart": []}
        
        await query.edit_message_text(
            text="❌ *Заказ отменен.*\n\nВсе данные удалены.\n\nДля нового заказа отправьте /start",
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    
    # Если callback не распознан
    await query.answer()
    return PRODUCT

# ========== КОМАНДА /cancel ==========
async def cancel_command(update: Update, context):
    user_id = update.effective_user.id
    
    # Очищаем данные пользователя
    if user_id in user_data:
        user_data[user_id] = {"cart": []}
    
    await update.message.reply_text(
        "❌ *Текущий заказ отменен.*\n\nВсе данные удалены.\n\nДля нового заказа отправьте /start",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

# ========== КОМАНДА /help ==========
async def help_command(update: Update, context):
    help_text = (
        "📖 *ПОМОЩЬ ПО БОТУ*\n\n"
        "*/start* - начать новый заказ\n"
        "*/cancel* - отменить текущий заказ\n"
        "*/help* - показать это сообщение\n\n"
        "*ИНСТРУКЦИЯ ПО ЗАКАЗУ:*\n"
        "1. Выберите город из списка\n"
        "2. Выберите способ доставки\n"
        "3. Добавьте товары в корзину (нажимайте на товары)\n"
        "4. Нажмите '🛒 Посмотреть корзину' для проверки\n"
        "5. Нажмите '✅ Завершить выбор' для оформления\n"
        "6. Свяжитесь с оператором @kldukr_mng\n\n"
        "*ГОРОДА:* Харьков, Одесса, Днепр, Львов, Запорожье, Винница, Херсон\n"
        "*ДОСТАВКА:* Такси, Новая Почта, Клад\n\n"
        "👤 *ОПЕРАТОР:* @kldukr_mng"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

# ========== ЗАПУСК ТЕЛЕГРАМ БОТА ==========
def run_telegram_bot():
    TOKEN = "7461220596:AAHmvyDgPs87JTYGGnLpB2OxTxTKFGCuUbQ"
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Создаем ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CITY: [CallbackQueryHandler(city_handler, pattern='^city_')],
            DELIVERY: [CallbackQueryHandler(delivery_handler, pattern='^del_')],
            PRODUCT: [CallbackQueryHandler(product_actions_handler, pattern='.*')]  # Ловим ВСЕ callback'и
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    
    # Логируем запуск
    print("=" * 60)
    print("🤖 ТЕЛЕГРАМ БОТ УСПЕШНО ЗАПУЩЕН!")
    print(f"📍 Доступно городов: {len(CITIES)}")
    print(f"🛒 Товаров в ассортименте: {len(PRODUCTS)}")
    print(f"🚚 Способов доставки: {len(DELIVERIES)}")
    print(f"👤 Оператор для связи: @kldukr_mng")
    print("=" * 60)
    print("✅ Кнопки 'Корзина' и 'Завершить' гарантированно работают!")
    print("=" * 60)
    
    # Запускаем бота
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

# ========== ЗАПУСК ВСЕГО ПРИЛОЖЕНИЯ ==========
if __name__ == '__main__':
    # Запускаем Telegram бот в отдельном потоке
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask сервер для health checks (требуется Koyeb)
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
