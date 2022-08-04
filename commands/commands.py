import os
from commands.bot_commands import bot_commands
from aiogram import types, Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from aiogram.dispatcher.filters import CommandObject
from .keyboards import get_accept_buttons, getvpn
from user_callback import UserCallbackData
from db.requests import create_user, ban_user
from gen_user import addUser

in_verification = set()

async def start(message: types.Message) -> types.Message:
    if not message.from_user.id in in_verification:
        await message.answer(
            'Если ты здесь, значит ты знаешь зачем...', 
            reply_markup=getvpn().as_markup(resize_keyboard=True)
        )

async def get_vpn(call: types.CallbackQuery, bot: Bot):
    in_verification.add(call.from_user.id)
    await bot.send_message(
        chat_id=os.getenv('ADMIN_ID'), 
        text= f"@{call.from_user.username} ({call.from_user.full_name}) отправил запрос на доступ.",
        reply_markup=get_accept_buttons(
            call.from_user.id, 
            call.from_user.username
        ).as_markup(resize_keyboard=True)
    )
    await call.message.delete()
    return await call.answer(
        'Ваш запрос отправлен на рассмотрение владельцу сервиса.',
        show_alert=True
    )

async def accept_event_user(call: types.CallbackQuery, session_maker: AsyncSession, bot: Bot, callback_data: UserCallbackData):
    pub_key, ip, config = await addUser(callback_data.name)
    user_data = {
        'id': callback_data.id,
        'name': callback_data.name,
        'pub_key': pub_key,
        'ip': ip
    }
    try:
        await create_user(user_data, session_maker)
        await call.message.edit_text(text=f"Пользователю {callback_data.name} доступ разрешен")
        await bot.send_document(callback_data.id, config, protect_content=True)
    except IntegrityError:
        await bot.send_message(callback_data.id, text='Вы уже зарегистрированы!')
        await call.answer('Пользователь уже зарегистрирован')
    in_verification.discard(int(callback_data.id))
    

async def decline_event_user(call: types.CallbackQuery, session_maker: AsyncSession, callback_data: UserCallbackData):
    try:
        await ban_user(session_maker, callback_data)
        await call.message.edit_text(text=f"Пользователю {callback_data.name} доступ запрещен")
    except IntegrityError:
        await call.answer('Не удалось забанить, что то пошло не так ...')
    in_verification.discard(int(callback_data.id))

async def help_command(message: types.Message, command: CommandObject) -> None:
    if command.args:
        for cmd in bot_commands:
            if cmd[0] == command.args:
                return await message.answer(f'{cmd[0]} - {cmd[1]}\n\n{cmd[2]}')
        else:
            return await message.answer('Команда не найдена')
    return await message.answer(
        'Помощь по боту\n Для получения информации о команде'
        'используйте /help <команда>\n'
    )

async def any_text(message: types.Message):
    await message.answer(text='Не известный запрос, используйте кнопки')