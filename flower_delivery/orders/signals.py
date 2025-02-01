import asyncio
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Order
from django.conf import settings

@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, created, **kwargs):
    if created:
        return

    user = instance.user
    if not user or not user.telegram_id:
        return

    # Допустим, нужно отправить сообщение
    async def send_message_to_user(telegram_id, text):
        # Импорт бота внутри функции, чтобы не было циклического импорта:
        from aiogram import Bot
        bot = Bot(token=settings.BOT_TOKEN)  # Или возьмите из настроек/окружения

        await bot.send_message(chat_id=telegram_id, text=text)
        await bot.session.close()  # Закрываем сессию

    async def runner():
        text = f"Ваш заказ #{instance.id} теперь в статусе {instance.get_status_display()}"
        await send_message_to_user(user.telegram_id, text)

    asyncio.run(runner())