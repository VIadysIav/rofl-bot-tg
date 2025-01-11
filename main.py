import random
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import datetime
import asyncio

async def raketka(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    chat_id = update.message.chat_id
    command_message = update.message

    # Проверка на необходимость извинений
    if context.user_data.get('awaiting_apology'):
        until_date = datetime.datetime.now() + datetime.timedelta(minutes=60)
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        response = await update.message.reply_text(
            "Ты проигнорировал требование извиниться и теперь отправляешься в мут на 1 час."
        )
        context.user_data['awaiting_apology'] = False
        asyncio.create_task(schedule_message_deletion(context, chat_id, [command_message.message_id, response.message_id]))
        return

    outcome = random.choices(['none', 'mute', 'ban', 'admin', 'rasstrel'], weights=[45, 45, 5, 1, 15], k=1)[0]

    if outcome == 'mute':
        until_date = datetime.datetime.now() + datetime.timedelta(minutes=15)
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        response = await update.message.reply_text(
            "В этот раз тебе повезло, и санитары уже проводят тебя в палату на целых 15 минут, подумай над своим поведением, слейв."
        )
        asyncio.create_task(schedule_message_deletion(context, chat_id, [command_message.message_id, response.message_id]))

    elif outcome == 'ban':
        response = await update.message.reply_text(
            "Тебе несказанно повезло, ты будешь забанен через 10 секунд. У тебя есть время для последнего слова!"
        )
        asyncio.create_task(schedule_message_deletion(context, chat_id, [command_message.message_id, response.message_id]))
        asyncio.create_task(handle_ban(context, chat_id, user.id))

    elif outcome == 'admin':
        await context.bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user.id,
            can_manage_chat=True,
            can_delete_messages=True
        )
        response = await update.message.reply_text(
            "Партия тобой не довольна, так как ты получил админские права на 3 минуты."
        )
        asyncio.create_task(revoke_admin_rights(context, chat_id, user.id, response))

    elif outcome == 'rasstrel':
        response = await update.message.reply_text(
            "Ты пользуешься ботом, но делаешь это без уважения. Напиши в чат: «Я прошу прощения у бота за то, что использую его в своих корыстных целях», и, может быть, я тебя прощу. У тебя есть полторы минуты"
        )
        context.user_data['awaiting_apology'] = True
        context.user_data['timeout_task'] = asyncio.create_task(timeout_check(update, context))
        context.user_data['expected_apology'] = "Я прошу прощения у бота за то, что использую его в своих корыстных целях"
        asyncio.create_task(schedule_message_deletion(context, chat_id, [command_message.message_id, response.message_id]))

    else:
        response = await update.message.reply_text(
            "В этот раз тебе не повезло, и ты ничего не выиграл, ну тупо лох."
        )
        asyncio.create_task(schedule_message_deletion(context, chat_id, [command_message.message_id, response.message_id]))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('awaiting_apology') and context.user_data.get('expected_apology'):
        user_text = update.message.text
        expected_text = context.user_data['expected_apology']
        
        if user_text.strip() == expected_text:
            # Случайное прощение или наказание
            forgive = random.choice([True, False])
            if forgive:
                context.user_data['awaiting_apology'] = False
                context.user_data['expected_apology'] = None
                await update.message.reply_text("Спасибо за извинения, на этот раз я тебя прощаю.")
            else:
                # Если бот не прощает — мут на 30 минут
                context.user_data['awaiting_apology'] = False
                until_date = datetime.datetime.now() + datetime.timedelta(minutes=30)
                await context.bot.restrict_chat_member(
                    chat_id=update.message.chat_id,
                    user_id=update.message.from_user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until_date
                )
                await update.message.reply_text("Твое извинение звучит неискренне, так что, старина, сьеби нахуй на 30 минут.")
        else:
            await update.message.reply_text("Это не то, что я просил сказать. Попробуй снова.")

async def handle_ban(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int):
    await asyncio.sleep(10)
    await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
    unban_response = await context.bot.send_message(chat_id, "Время истекло! Ты забанен на 1 минуту.")
    await asyncio.sleep(60)
    await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
    await context.bot.send_message(chat_id, "Ты был разбанен через 1 минуту. Добро пожаловать обратно!")

async def revoke_admin_rights(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int, response):
    await asyncio.sleep(180)
    await context.bot.promote_chat_member(
        chat_id=chat_id,
        user_id=user_id,
        can_manage_chat=False,
        can_delete_messages=False
    )
    revoke_response = await context.bot.send_message(chat_id, "Твои админские права истекли через 3 минуты.")
    asyncio.create_task(schedule_message_deletion(context, chat_id, [response.message_id, revoke_response.message_id]))

async def timeout_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(90)
    if context.user_data.get('awaiting_apology'):
        context.user_data['awaiting_apology'] = False
        until_date = datetime.datetime.now() + datetime.timedelta(minutes=60)
        await context.bot.restrict_chat_member(
            chat_id=update.message.chat_id,
            user_id=update.message.from_user.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        await context.bot.send_message(update.message.chat_id, "Ты думаешь что самый умный? Даю тебе 1 час на подумать")

async def schedule_message_deletion(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_ids: list[int]):
    await asyncio.sleep(900)  # Удаление через 15 минут
    for message_id in message_ids:
        try:
            await context.bot.delete_message(chat_id, message_id)
        except:
            pass

def main():
    application = Application.builder().token('YOUR_BOT_TOKEN').build()

    application.add_handler(CommandHandler("raketka", raketka))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling()

if __name__ == "__main__":
    main()
