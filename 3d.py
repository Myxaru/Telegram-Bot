import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация бота
BOT_TOKEN = "8106031721:AAFP808M6HZH2pGuFGQjPCb-sWnRkDYbBJM"
GROUP_CHAT_ID = -4912732887

# Разрешенные форматы файлов
ALLOWED_3D_FILES = {'stl', 'obj', '3mf', 'amf', 'step', 'stp'}
ALLOWED_IMAGES = {'jpg', 'jpeg', 'png', 'gif'}
ALLOWED_EXTENSIONS = ALLOWED_3D_FILES | ALLOWED_IMAGES

# Состояния формы
(
    START,
    FILE_OR_LINK,
    MODEL_NAME,
    DESCRIPTION,
    WHEEL_COMPAT,
    PRINT_SETTINGS,
    IS_AUTHOR,
    AUTHOR_INFO,
    THINGIVERSE,
    SHOW_AUTHOR,
    FINISH
) = range(11)

# Тексты сообщений
WELCOME_TEXT = """
<b>🌟 Добро пожаловать в бот для публикации 3D-моделей! 🌟</b>

Здесь вы можете поделиться своими разработками для моноколёс, чтобы мы разместили их на сайте eucer.ru для свободного скачивания.

<b>📌 Как это работает:</b>
1. Вы отправляете модель (файл или ссылку)
2. Добавляете информацию о модели
3. Мы проверяем и публикуем её на сайте

Выберите действие:
"""

ABOUT_TEXT = """
<b>🤖 О боте и публикации моделей</b>

Этот бот создан для сбора 3D-моделей, связанных с моноколёсами, и их последующей публикации на сайте eucer.ru.
Мы принимаем как файлы моделей, так и ссылки на уже опубликованные детали на таких источниках, как thingyverse, cult3D и др.
Можно отправлять и сслыки на файлы, размещенные в telegram. В общем, всё для вашего удобства. 

<b>🔧 Что происходит после отправки:</b>
1) Если 3Д модель разрабатывали НЕ вы:
• В случае отправки файла с 3D моделью, не забудьте указать название и описание модели, а также прочую информацию. 
• Если отправляете сслыку на thingyverse, cult3D и т.д. - описание мы можем взять оттуда.
• По возможности укажите, для каких моделей моноколёс эта модель подходит. 


2) Если вы - авто 3D модели:
• Можете выслать ссылку на опубликованную с описанием модель 
либо (если вам лень) мы опубликуем сами Для этого:
• Напишите описание и параметры, ответьте на прочие вопросы формы
• По возможности укажите, для каких моделей моноколёс эта модель подходит. 
• Дайте согласие на публикацию модели от eucer.ru
• Укажите, необходимо ли при публикации указывать ваше авторство.
• При желании можете указать контакты для обратной связи.

Что сделаем мы:
• Cами разместим вашу модель на сайте thingyverse от аккаунта eucer.ru (если получено разрешение).
• Создадим картинки с 3D визуализацией вашей модели
• Сделаем страницу на сайте, заполним все аттрибуты для фильтров
• Предоставим доступ для скачивания всем пользователям

<b>📌 Важно:</b>
• Принимаются только 3D модели для моноколёс
• Авторские права остаются за автором
"""

FILE_REQUIREMENTS = """
<b>📌 Требования к файлам:</b>
• <b>3D-модели:</b> STL, OBJ, 3MF, STEP, STP
• <b>Изображения:</b> JPG, PNG (для визуализации)
• <b>Макс. размер:</b> 50 MB

<b>❗ Если отправляете файл:</b>
1. Прикрепите файл к сообщению
2. Добавьте подпись (если нужно)
"""

EXAMPLE_NAMES = [
    "🔹 Крепление фонаря на Kingsong 16X",
    "🔹 Защита платы InMotion V11",
    "🔹 Ручка для переноски Gotway MSX"
]

EXAMPLE_DESCRIPTIONS = [
    "🔹 Крепление позволяет установить фонарь на руль без сверления. Подходит для печати на FDM принтерах.",
    "🔹 Защита от воды и грязи для контроллера. Легко устанавливается на штатные крепления.",
    "🔹 Эргономичная ручка для переноски моноколёса. Печать с заполнением 20%."
]

# Клавиатуры
def main_menu():
    return ReplyKeyboardMarkup([
        ["📤 Отправить модель", "ℹ️ О боте"]
    ], resize_keyboard=True)

def skip_or_finish():
    return ReplyKeyboardMarkup([
        ["⏭ Пропустить", "✅ Завершить"],
        ["❌ Отмена"]
    ], resize_keyboard=True)

def yes_no_keyboard():
    return ReplyKeyboardMarkup([
        ["✅ Да", "❌ Нет"],
        ["❌ Отмена"]
    ], resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup([
        ["❌ Отмена"]
    ], resize_keyboard=True)

def get_reply_button(user_id):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✉️ Ответить автору", url=f"tg://user?id={user_id}")
    ]])

# Вспомогательные функции
def is_allowed_file(filename):
    if not filename:
        return False
    ext = filename.split('.')[-1].lower()
    return ext in ALLOWED_EXTENSIONS

def is_3d_file(filename):
    ext = filename.split('.')[-1].lower()
    return ext in ALLOWED_3D_FILES

def is_link(text):
    if not text:
        return False
    return text.startswith(('http://', 'https://', 'www.'))

def format_user_info(user):
    return (
        f"👤 <b>Автор:</b> {user.full_name}\n"
        f"📱 <b>Username:</b> @{user.username if user.username else 'нет'}\n"
        f"🆔 <b>ID:</b> {user.id}\n"
    )

async def forward_to_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Функция для пересылки сообщений в чат администраторов"""
    user = update.effective_user
    admin_message = format_user_info(user) + "\n<b>📨 Сообщение от пользователя:</b>\n\n"
    
    if update.message.text:
        admin_message += update.message.text
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=admin_message,
            parse_mode='HTML',
            reply_markup=get_reply_button(user.id)
        )
    elif update.message.document:
        admin_message += f"📄 <b>Файл:</b> {update.message.document.file_name}"
        if update.message.caption:
            admin_message += f"\n📝 <b>Подпись:</b> {update.message.caption}"
        
        await context.bot.send_document(
            chat_id=GROUP_CHAT_ID,
            document=update.message.document.file_id,
            caption=admin_message,
            parse_mode='HTML',
            reply_markup=get_reply_button(user.id)
        )
    elif update.message.photo:
        admin_message += "🖼 <b>Фото</b>"
        if update.message.caption:
            admin_message += f"\n📝 <b>Подпись:</b> {update.message.caption}"
        
        await context.bot.send_photo(
            chat_id=GROUP_CHAT_ID,
            photo=update.message.photo[-1].file_id,
            caption=admin_message,
            parse_mode='HTML',
            reply_markup=get_reply_button(user.id)
        )
    elif update.message.video:
        admin_message += "🎥 <b>Видео</b>"
        if update.message.caption:
            admin_message += f"\n📝 <b>Подпись:</b> {update.message.caption}"
        
        await context.bot.send_video(
            chat_id=GROUP_CHAT_ID,
            video=update.message.video.file_id,
            caption=admin_message,
            parse_mode='HTML',
            reply_markup=get_reply_button(user.id)
        )

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=main_menu(),
        parse_mode='HTML'
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        ABOUT_TEXT,
        reply_markup=main_menu(),
        parse_mode='HTML'
    )

# Обработчики формы
async def form_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "<b>1. Пришлите файл 3D-модели или ссылку:</b>\n\n" + FILE_REQUIREMENTS,
        reply_markup=cancel_keyboard(),
        parse_mode='HTML'
    )
    return FILE_OR_LINK

async def handle_file_or_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel_form(update, context)
    
    if update.message.document:
        if not is_allowed_file(update.message.document.file_name):
            await update.message.reply_text(
                "<b>⚠️ Неподдерживаемый формат файла!</b>\n\n" + FILE_REQUIREMENTS,
                reply_markup=cancel_keyboard(),
                parse_mode='HTML'
            )
            return FILE_OR_LINK
        
        context.user_data['file'] = {
            'id': update.message.document.file_id,
            'name': update.message.document.file_name
        }
        context.user_data['is_3d'] = is_3d_file(update.message.document.file_name)
        
        if update.message.caption:
            context.user_data['file_caption'] = update.message.caption
        
        await update.message.reply_text(
            "<b>2. Укажите название модели:</b>\n\n"
            "<i>📌 Примеры хороших названий:</i>\n" + "\n".join(EXAMPLE_NAMES),
            reply_markup=cancel_keyboard(),
            parse_mode='HTML'
        )
        return MODEL_NAME
    
    elif update.message.text and is_link(update.message.text):
        context.user_data['link'] = update.message.text
        await update.message.reply_text(
            "<b>2. Укажите название модели (или пропустите):</b>\n\n"
            "<i>📌 Примеры:</i>\n" + "\n".join(EXAMPLE_NAMES),
            reply_markup=skip_or_finish(),
            parse_mode='HTML'
        )
        return MODEL_NAME
    
    await update.message.reply_text(
        "<b>Пожалуйста, пришлите файл 3D-модели или ссылку</b>",
        reply_markup=cancel_keyboard(),
        parse_mode='HTML'
    )
    return FILE_OR_LINK

async def handle_model_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel_form(update, context)
    
    if update.message.text == "⏭ Пропустить":
        if 'link' in context.user_data:
            await update.message.reply_text(
                "<b>3. Добавьте описание модели (или пропустите):</b>\n\n"
                "<i>📌 Что стоит указать:</i>\n"
                "- Назначение детали\n"
                "- Особенности установки\n"
                "- Преимущества конструкции\n\n"
                "<i>Примеры:</i>\n" + "\n".join(EXAMPLE_DESCRIPTIONS),
                reply_markup=skip_or_finish(),
                parse_mode='HTML'
            )
            return DESCRIPTION
        await update.message.reply_text(
            "<b>⚠️ Для файлов название обязательно!</b>",
            reply_markup=cancel_keyboard(),
            parse_mode='HTML'
        )
        return MODEL_NAME
    
    if update.message.text == "✅ Завершить":
        return await finish_form(update, context)
    
    context.user_data['model_name'] = update.message.text
    await update.message.reply_text(
        "<b>3. Опишите модель:</b>\n\n"
        "<i>📌 Что стоит указать:</i>\n"
        "- Для чего эта деталь\n"
        "- Как устанавливается\n"
        "- Какие проблемы решает\n\n"
        "<i>Примеры:</i>\n" + "\n".join(EXAMPLE_DESCRIPTIONS),
        reply_markup=skip_or_finish() if 'link' in context.user_data else cancel_keyboard(),
        parse_mode='HTML'
    )
    return DESCRIPTION

async def handle_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel_form(update, context)
    
    if update.message.text == "⏭ Пропустить":
        if 'link' in context.user_data:
            await update.message.reply_text(
                "<b>4. Для каких моноколёс подходит?</b>\n\n"
                "<i>📌 Примеры:</i>\n"
                "- Kingsong 16X, 18XL\n"
                "- Все моноколёса с диаметром 18\"\n"
                "- InMotion V11/V12",
                reply_markup=skip_or_finish(),
                parse_mode='HTML'
            )
            return WHEEL_COMPAT
        await update.message.reply_text(
            "<b>⚠️ Для файлов описание обязательно!</b>",
            reply_markup=cancel_keyboard(),
            parse_mode='HTML'
        )
        return DESCRIPTION
    
    if update.message.text == "✅ Завершить":
        return await finish_form(update, context)
    
    context.user_data['description'] = update.message.text
    await update.message.reply_text(
        "<b>4. Для каких моделей подходит?</b>\n\n"
        "<i>📌 Можно указать:</i>\n"
        "- Конкретные модели (Kingsong 16X)\n"
        "- Характеристики (колёса 18\" и больше)\n"
        "- Особые требования",
        reply_markup=skip_or_finish(),
        parse_mode='HTML'
    )
    return WHEEL_COMPAT

async def handle_wheel_compat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel_form(update, context)
    
    if update.message.text not in ["⏭ Пропустить", "✅ Завершить"]:
        context.user_data['wheel_compat'] = update.message.text
    
    if update.message.text == "✅ Завершить":
        return await finish_form(update, context)
    
    await update.message.reply_text(
        "<b>5. Рекомендации по печати:</b>\n\n"
        "<i>📌 Что указать:</i>\n"
        "- Материал (PLA, PETG, ABS)\n"
        "- Настройки печати\n"
        "- Необходимость поддержек\n\n"
        "<i>Пример:</i> PETG, 100% заполнение, стенки 1.2мм, поддержки нужны",
        reply_markup=skip_or_finish(),
        parse_mode='HTML'
    )
    return PRINT_SETTINGS

async def handle_print_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel_form(update, context)
    
    if update.message.text not in ["⏭ Пропустить", "✅ Завершить"]:
        context.user_data['print_settings'] = update.message.text
    
    if update.message.text == "✅ Завершить":
        return await finish_form(update, context)
    
    await update.message.reply_text(
        "<b>6. Вы автор этой модели?</b>\n\n"
        "<i>Это поможет правильно указать авторство на сайте</i>",
        reply_markup=yes_no_keyboard(),
        parse_mode='HTML'
    )
    return IS_AUTHOR

async def handle_is_author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel_form(update, context)
    
    if update.message.text not in ["✅ Да", "❌ Нет"]:
        await update.message.reply_text(
            "Пожалуйста, выберите Да или Нет",
            reply_markup=yes_no_keyboard()
        )
        return IS_AUTHOR
    
    context.user_data['is_author'] = update.message.text == "✅ Да"
    
    if context.user_data['is_author']:
        await update.message.reply_text(
            "<b>7. Как вас указать как автора?</b>\n\n"
            "<i>📌 Примеры:</i>\n"
            "- Иван Петров\n"
            "- @monowheel_designer\n"
            "- Максим (Telegram: @max_msk)",
            reply_markup=skip_or_finish(),
            parse_mode='HTML'
        )
        return AUTHOR_INFO
    
    return await finish_form(update, context)

async def handle_author_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel_form(update, context)
    
    if update.message.text == "⏭ Пропустить":
        await update.message.reply_text(
            "<b>8. Разрешаете опубликовать на Thingiverse?</b>\n\n"
            "<i>Мы можем разместить модель на нашем аккаунте thingiverse.com/eucer_ru</i>",
            reply_markup=yes_no_keyboard(),
            parse_mode='HTML'
        )
        return THINGIVERSE
    
    if update.message.text == "✅ Завершить":
        return await finish_form(update, context)
    
    context.user_data['author_info'] = update.message.text
    await update.message.reply_text(
        "<b>8. Разрешаете опубликовать на Thingiverse?</b>\n\n"
        "<i>Мы можем разместить модель на нашем аккаунте thingiverse.com/eucer_ru</i>",
        reply_markup=yes_no_keyboard(),
        parse_mode='HTML'
    )
    return THINGIVERSE

async def handle_thingiverse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel_form(update, context)
    
    if update.message.text not in ["✅ Да", "❌ Нет"]:
        await update.message.reply_text(
            "Пожалуйста, выберите Да или Нет",
            reply_markup=yes_no_keyboard()
        )
        return THINGIVERSE
    
    context.user_data['thingiverse'] = update.message.text == "✅ Да"
    await update.message.reply_text(
        "<b>9. Показывать вас как автора на сайте?</b>\n\n"
        "<i>Ваше имя/ник будет указано на странице модели</i>",
        reply_markup=yes_no_keyboard(),
        parse_mode='HTML'
    )
    return SHOW_AUTHOR

async def handle_show_author(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "❌ Отмена":
        return await cancel_form(update, context)
    
    if update.message.text not in ["✅ Да", "❌ Нет"]:
        await update.message.reply_text(
            "Пожалуйста, выберите Да или Нет",
            reply_markup=yes_no_keyboard()
        )
        return SHOW_AUTHOR
    
    context.user_data['show_author'] = update.message.text == "✅ Да"
    return await finish_form(update, context)

async def finish_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        admin_message = format_user_info(user) + "<b>📤 Новая модель для сайта</b>\n\n"
        
        if 'file' in context.user_data:
            file_info = (
                f"📄 <b>Файл:</b> {context.user_data['file']['name']}\n"
                f"🔢 <b>Тип:</b> {'3D-модель' if context.user_data['is_3d'] else 'Изображение'}\n"
            )
            if context.user_data.get('file_caption'):
                file_info += f"📝 <b>Подпись:</b> {context.user_data['file_caption']}\n"
            
            admin_message += file_info
        elif 'link' in context.user_data:
            admin_message += f"🔗 <b>Ссылка:</b> {context.user_data['link']}\n"
        
        # Добавляем информацию о модели
        model_info = []
        if 'model_name' in context.user_data:
            model_info.append(f"🏷 <b>Название:</b> {context.user_data['model_name']}")
        if 'description' in context.user_data:
            model_info.append(f"📝 <b>Описание:</b> {context.user_data['description']}")
        if 'wheel_compat' in context.user_data:
            model_info.append(f"🛴 <b>Для моделей:</b> {context.user_data['wheel_compat']}")
        if 'print_settings' in context.user_data:
            model_info.append(f"🖨 <b>Печать:</b> {context.user_data['print_settings']}")
        
        if model_info:
            admin_message += "\n\n" + "\n".join(model_info)
        
        # Информация об авторе
        if context.user_data.get('is_author', False):
            author_info = []
            if 'author_info' in context.user_data:
                author_info.append(f"👤 <b>Автор:</b> {context.user_data['author_info']}")
            if 'thingiverse' in context.user_data:
                author_info.append(f"🌐 <b>Thingiverse:</b> {'Да' if context.user_data['thingiverse'] else 'Нет'}")
            if 'show_author' in context.user_data:
                author_info.append(f"👀 <b>Показывать автора:</b> {'Да' if context.user_data['show_author'] else 'Нет'}")
            
            if author_info:
                admin_message += "\n\n" + "\n".join(author_info)
        
        # Отправляем файл/ссылку
        if 'file' in context.user_data:
            await context.bot.send_document(
                chat_id=GROUP_CHAT_ID,
                document=context.user_data['file']['id'],
                caption=admin_message,
                parse_mode='HTML',
                reply_markup=get_reply_button(user.id)
            )
        else:
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=admin_message,
                parse_mode='HTML',
                reply_markup=get_reply_button(user.id)
            )
        
        await update.message.reply_text(
            "<b>✅ Спасибо! Ваша модель отправлена на модерацию.</b>\n\n"
            "После проверки она будет опубликована на сайте eucer.ru",
            reply_markup=main_menu(),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(
            "<b>⚠️ Произошла ошибка при отправке</b>\nПожалуйста, попробуйте позже.",
            reply_markup=main_menu(),
            parse_mode='HTML'
        )
    finally:
        context.user_data.clear()
        return ConversationHandler.END

async def cancel_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Отправка отменена",
        reply_markup=main_menu()
    )
    return ConversationHandler.END

async def handle_regular_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик обычных сообщений вне формы"""
    if update.message.text in ["📤 Отправить модель", "ℹ️ О боте", "❌ Отмена"]:
        return
    
    try:
        await forward_to_admins(update, context)
        await update.message.reply_text(
            "✅ Ваше сообщение переслано администраторам",
            reply_markup=main_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка при пересылке сообщения: {e}")
        await update.message.reply_text(
            "⚠️ Не удалось переслать сообщение администраторам",
            reply_markup=main_menu()
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")
    try:
        await update.message.reply_text(
            "<b>⚠️ Произошла ошибка</b>\nПожалуйста, попробуйте еще раз.",
            reply_markup=main_menu(),
            parse_mode='HTML'
        )
    except:
        pass

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_error_handler(error_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex(r'^ℹ️ О боте$'), about))
    
    form_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^📤 Отправить модель$'), form_start)],
        states={
            FILE_OR_LINK: [MessageHandler(filters.ALL, handle_file_or_link)],
            MODEL_NAME: [MessageHandler(filters.TEXT, handle_model_name)],
            DESCRIPTION: [MessageHandler(filters.TEXT, handle_description)],
            WHEEL_COMPAT: [MessageHandler(filters.TEXT, handle_wheel_compat)],
            PRINT_SETTINGS: [MessageHandler(filters.TEXT, handle_print_settings)],
            IS_AUTHOR: [MessageHandler(filters.TEXT, handle_is_author)],
            AUTHOR_INFO: [MessageHandler(filters.TEXT, handle_author_info)],
            THINGIVERSE: [MessageHandler(filters.TEXT, handle_thingiverse)],
            SHOW_AUTHOR: [MessageHandler(filters.TEXT, handle_show_author)],
        },
        fallbacks=[MessageHandler(filters.Regex(r'^❌ Отмена$'), cancel_form)],
    )
    
    # Обработчик для обычных сообщений вне формы
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.Regex(r'^(📤 Отправить модель|ℹ️ О боте|❌ Отмена)$') & ~filters.COMMAND,
        handle_regular_message
    ))
    
    # Обработчик для медиафайлов вне формы
    application.add_handler(MessageHandler(
        (filters.Document.ALL | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND,
        handle_regular_message
    ))
    
    application.add_handler(form_conv)
    application.run_polling()

if __name__ == '__main__':
    main()
