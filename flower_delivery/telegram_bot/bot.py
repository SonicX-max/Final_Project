import os
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
import sys
import django

# Инициализация Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "flower_delivery.settings")
django.setup()

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils import executor
from asgiref.sync import sync_to_async

from django.conf import settings
from django.contrib.auth import get_user_model
from products.models import Product
from orders.models import Order, OrderItem

from datetime import date, timedelta

User = get_user_model()

BOT_TOKEN = settings.BOT_TOKEN  # Токен из settings.py
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

print(f"[DEBUG] DB NAME = {settings.DATABASES['default']['NAME']}")

# --- Состояния (FSM) для оформления заказа ---
class OrderFSM(StatesGroup):
    waiting_for_product_name = State()
    waiting_for_quantity = State()
    waiting_for_address = State()
    waiting_for_phone = State()

# --- Состояние для запроса периода в днях (аналитика) ---
class AnalyticsFSM(StatesGroup):
    waiting_for_days = State()

# ------------------------------------------------------------------------
# ГЛОБАЛЬНЫЙ ХЕНДЛЕР: если пользователь в любом состоянии нажал одну
# из команд ("Сделать заказ", "Проверить статус заказа", "Аналитика"),
# то завершаем предыдущую FSM и переходим к нужной логике.
# ------------------------------------------------------------------------
@dp.message_handler(Text(equals=["Сделать заказ", "Проверить статус заказа", "Аналитика"]), state="*")
async def global_menu_handler(message: types.Message, state: FSMContext):
    # Завершаем текущее состояние (если было)
    await state.finish()

    if message.text == "Сделать заказ":
        await start_order_process(message)
    elif message.text == "Проверить статус заказа":
        await check_order_status(message)
    elif message.text == "Аналитика":
        # Сначала проверяем, что пользователь админ
        is_admin = await sync_to_async(User.objects.filter(
            username=message.from_user.username,
            is_staff=True
        ).exists)()
        if not is_admin:
            await message.answer("У вас нет прав для просмотра аналитики.")
            return

        # Если админ — спрашиваем, за сколько дней показывать отчёт
        await message.answer("Введите, за сколько дней показать аналитику (число).")
        await AnalyticsFSM.waiting_for_days.set()

# ------------------------------------------------------------------------
# Хендлер /start: показывает меню
# ------------------------------------------------------------------------
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
    main_menu.add(KeyboardButton("Сделать заказ"))
    main_menu.add(KeyboardButton("Проверить статус заказа"))

    # Проверка: является ли пользователь админом
    is_admin = await sync_to_async(User.objects.filter(
        username=message.from_user.username,
        is_staff=True
    ).exists)()

    if is_admin:
        main_menu.add(KeyboardButton("Аналитика"))

    await message.answer(
        "Добро пожаловать в бот доставки цветов!\n"
        "Вы можете сделать заказ или проверить статус уже созданного заказа.",
        reply_markup=main_menu
    )

# ------------------------------------------------------------------------
# 1) ЛОГИКА ОФОРМЛЕНИЯ ЗАКАЗА (FSM)
# ------------------------------------------------------------------------
async def start_order_process(message: types.Message):
    await message.answer("Какой букет хотите заказать? (Введите название)")
    await OrderFSM.waiting_for_product_name.set()

@dp.message_handler(state=OrderFSM.waiting_for_product_name)
async def fsm_product_name(message: types.Message, state: FSMContext):
    product_name = message.text.strip()
    await state.update_data(product_name=product_name)
    await message.answer("Сколько штук?")
    await OrderFSM.waiting_for_quantity.set()

@dp.message_handler(state=OrderFSM.waiting_for_quantity)
async def fsm_quantity(message: types.Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите целое число (например, 3).")
        return

    await state.update_data(quantity=qty)
    await message.answer("Укажите адрес доставки:")
    await OrderFSM.waiting_for_address.set()

@dp.message_handler(state=OrderFSM.waiting_for_address)
async def fsm_address(message: types.Message, state: FSMContext):
    address = message.text.strip()
    await state.update_data(address=address)
    await message.answer("Укажите контактный телефон (например, +7 999 999-99-99):")
    await OrderFSM.waiting_for_phone.set()

@dp.message_handler(state=OrderFSM.waiting_for_phone)
async def fsm_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    data = await state.get_data()

    product_name = data["product_name"]
    qty = data["quantity"]
    address = data["address"]

    @sync_to_async
    def create_order_in_db(tg_id, tg_username, product_name, qty, address, phone):
        product, _ = Product.objects.get_or_create(
            name=product_name,
            defaults={'price': 100}
        )
        user = User.objects.filter(telegram_id=tg_id).first()
        if not user:
            user = User.objects.filter(username=tg_username).first()

        if not user:
            user = User.objects.create_user(
                username=tg_username or f"guest_{tg_id}",
                password="default_password",
                phone=phone
            )
            user.telegram_id = tg_id
            user.save()
        else:
            if not user.telegram_id:
                user.telegram_id = tg_id
                user.save()

        order = Order.objects.create(
            user=user,
            status='new',
            address=address,
            phone=phone
        )
        OrderItem.objects.create(order=order, product=product, quantity=qty)
        return order

    order = await create_order_in_db(
        message.from_user.id,
        message.from_user.username,
        product_name,
        qty,
        address,
        phone
    )

    await message.answer(
        f"Заказ создан!\n"
        f"Номер заказа: {order.id}\n"
        "Мы свяжемся с вами для подтверждения."
    )
    await state.finish()

# ------------------------------------------------------------------------
# 2) ЛОГИКА ПРОВЕРКИ СТАТУСА ЗАКАЗА
# ------------------------------------------------------------------------
async def check_order_status(message: types.Message):
    """
    Просим ввести номер заказа.
    """
    await message.answer("Введите номер вашего заказа (число).")

@dp.message_handler()
async def handle_order_id(message: types.Message):
    """
    Если пользователь ввёл число (ID заказа) — показываем статус.
    Иначе игнорируем.
    """
    try:
        order_id = int(message.text.strip())
    except ValueError:
        return

    @sync_to_async
    def get_order_and_sum(o_id):
        order = Order.objects.get(id=o_id)
        total_price = sum(
            item.product.price * item.quantity
            for item in order.orderitem_set.all()
        )
        status_display = order.get_status_display()
        created_str = order.created_at.strftime('%d.%m.%Y %H:%M')
        return (order, total_price, status_display, created_str)

    try:
        order, total_price, status_display, created_str = await get_order_and_sum(order_id)
        await message.answer(
            f"Информация о заказе:\n"
            f"Номер заказа: {order.id}\n"
            f"Статус: {status_display}\n"
            f"Общая сумма: {total_price} руб.\n"
            f"Дата создания: {created_str}"
        )
    except Order.DoesNotExist:
        await message.answer("Заказ с таким номером не найден.")

# ------------------------------------------------------------------------
# 3) ЛОГИКА АНАЛИТИКИ (через FSM, чтобы спросить кол-во дней)
# ------------------------------------------------------------------------
@dp.message_handler(state=AnalyticsFSM.waiting_for_days)
async def process_analytics_days(message: types.Message, state: FSMContext):
    """
    Пользователь (админ) ввёл число дней. Фильтруем заказы за этот период,
    выводим подробную инфу: статус, адрес, телефон, список товаров, сумма и т.д.
    """
    try:
        days = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите целое число дней.")
        return

    # Считаем период
    today = date.today()
    start_date = today - timedelta(days=days)

    # Фильтруем заказы, создавшиеся после start_date
    @sync_to_async
    def fetch_orders_and_items(start_date):
        orders = Order.objects.filter(created_at__gte=start_date).order_by('-created_at')
        # Можно в цикле или позже вычислить сумму
        return list(orders)

    orders_list = await fetch_orders_and_items(start_date)

    # Подсчитываем общую выручку
    @sync_to_async
    def calc_total_revenue(orders):
        items = OrderItem.objects.filter(order__in=orders)
        return sum(it.quantity * it.product.price for it in items)

    total_revenue = await calc_total_revenue(orders_list)
    total_orders = len(orders_list)

    # Формируем ответ
    text = (
        f"Аналитика за последние {days} дней:\n"
        f"Всего заказов: {total_orders}\n"
        f"Суммарная выручка: {total_revenue} руб.\n\n"
    )

    if total_orders == 0:
        text += "Заказов не найдено."
    else:
        # Перечислим заказы
        for order in orders_list:
            items = await sync_to_async(lambda o: list(o.orderitem_set.all()))(order)
            sum_order = sum(i.product.price * i.quantity for i in items)
            text += (f"Заказ №{order.id} [{order.created_at.strftime('%d.%m.%Y %H:%M')}]\n"
                     f"Статус: {order.get_status_display()}\n"
                     f"Адрес: {order.address}\n"
                     f"Телефон: {order.phone}\n"
                     f"Сумма: {sum_order} руб.\n"
                     "Товары:\n")
            for it in items:
                text += f" - {it.product.name} x{it.quantity} (цена: {it.product.price} руб.)\n"
            text += "\n"

    # Отправляем результат (учитывая возможный лимит ~4096 символов, если очень много заказов).
    # Простым вариантом отправляем всё в одном сообщении:
    if len(text) < 4000:
        await message.answer(text)
    else:
        # Разбиваем на части, если очень длинно (пример):
        chunks = [text[i:i+3500] for i in range(0, len(text), 3500)]
        for chunk in chunks:
            await message.answer(chunk)

    await state.finish()

# ------------------------------------------------------------------------
# Запуск бота
# ------------------------------------------------------------------------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)