"""
Russian lexicon for finance bot.
UX texts following "Write, Cut" principles: short, clear, friendly.
"""

LEXICON_RU: dict[str, str] = {
    # Commands
    "start_welcome": (
        "👋 Привет, {name}!\n\n"
        "Я помогу вести учёт финансов. "
        "Записывай доходы и расходы текстом или голосом — "
        "я сам определю категорию.\n\n"
        "Выбери действие 👇"
    ),
    
    "start_welcome_back": (
        "👋 С возвращением, {name}!\n\n"
        "Чем займёмся? 👇"
    ),
    
    # Main menu buttons
    "btn_add_transaction": "➕ Добавить",
    "btn_categories": "📂 Категории",
    "btn_reports": "📊 Отчёты",
    "btn_help": "❓ Помощь",
    
    # Add transaction
    "add_choose_type": "Что записываем?",
    "btn_income": "💰 Доход",
    "btn_expense": "💸 Расход",
    "btn_back": "◀️ Назад",
    "btn_cancel": "❌ Отмена",
    
    "add_enter_text": (
        "📝 Опиши {type}.\n\n"
        "Например: «{example}»\n\n"
        "Можно отправить голосовое 🎤"
    ),
    "income_example": "зарплата 50000",
    "expense_example": "кофе 35000 сумов",
    
    "transaction_saved": (
        "✅ Записано!\n\n"
        "{type}: {amount} сўм\n"
        "Категория: {category}"
    ),
    "transaction_duplicate": "⚠️ Похожая запись уже добавлена. Подожди минуту.",
    
    # Categories
    "categories_title": "📂 Твои категории",
    "categories_empty": "Категорий пока нет. Они создадутся автоматически при добавлении записей.",
    "btn_add_category": "➕ Создать",
    "btn_edit_categories": "✏️ Изменить",
    "btn_delete_categories": "🗑 Удалить",
    "btn_income_categories": "💰 Доходы",
    "btn_expense_categories": "💸 Расходы",
    
    "category_choose_type": "Выбери тип категории:",
    "category_enter_name": "Введи название категории:",
    "category_enter_new_name": "Введи новое название для «{name}»:",
    "category_created": "✅ Категория «{name}» создана!",
    "category_updated": "✅ Категория переименована в «{name}»",
    "category_exists": "⚠️ Такая категория уже есть.",
    "category_deleted": "🗑 Категория «{name}» удалена.",
    "category_has_transactions": "⚠️ Нельзя удалить — есть {count} связанных записей.",
    "category_select_to_edit": "Выбери категорию для редактирования:",
    "category_select_to_delete": "Выбери категорию для удаления:",
    "category_confirm_delete": "Удалить категорию «{name}»?",
    "btn_confirm_delete": "🗑 Да, удалить",
    
    # Reports
    "reports_choose_month": "📊 За какой месяц показать отчёт?",
    "report_title": "📊 Отчёт за {month}",
    "report_income": "💰 Доходы: {amount} сўм",
    "report_expense": "💸 Расходы: {amount} сўм",
    "report_balance": "📈 Баланс: {amount} сўм",
    "report_by_category": "\n📁 По категориям:\n{details}",
    "report_empty": "За этот месяц записей нет.",
    "report_transactions_count": "\n📝 Всего записей: {count}",
    
    # Months
    "month_1": "Январь",
    "month_2": "Февраль",
    "month_3": "Март",
    "month_4": "Апрель",
    "month_5": "Май",
    "month_6": "Июнь",
    "month_7": "Июль",
    "month_8": "Август",
    "month_9": "Сентябрь",
    "month_10": "Октябрь",
    "month_11": "Ноябрь",
    "month_12": "Декабрь",
    
    # Help
    "help_text": (
        "❓ <b>Как пользоваться</b>\n\n"
        "1️⃣ <b>Добавить запись</b>\n"
        "Напиши или отправь голосовое.\n"
        "Пример: «потратил 500 на такси»\n\n"
        "2️⃣ <b>Категории</b>\n"
        "Создаются автоматически или вручную.\n\n"
        "3️⃣ <b>Отчёты</b>\n"
        "Статистика за любой месяц.\n\n"
        "📌 Данные хранятся 6 месяцев."
    ),
    
    # Errors
    "error_unknown": "😔 Что-то пошло не так. Попробуй ещё раз.",
    "error_invalid_amount": "⚠️ Не удалось определить сумму. Укажи число.",
    "error_too_fast": "⏳ Слишком много запросов. Подожди немного.",
    "error_text_too_long": "⚠️ Сообщение слишком длинное. Сократи до 500 символов.",
    "error_voice_too_long": "⚠️ Голосовое слишком длинное. Максимум 5 минут.",
    
    # Processing
    "processing": "⏳ Обрабатываю...",
    "voice_recognized": "🎤 <i>«{text}»</i>\n\n",
}
