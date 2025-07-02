import logging
import sqlite3
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

# Конфигурация активностей - здесь легко добавлять новые
ACTIVITIES = {
    'pushup': {
        'table': 'pushups',
        'emoji': '🔥',
        'unit': '',
        'name': 'Отжимания',
        'name_gen': 'анжуманий',
        'milestones': [100, 250, 500, 1000, 2500, 5000, 10000],
        'messages': {
            100: "🎉 Поздравляем! Вы достигли 100 анжуманий! еще бегит не забывай! 💪",
            250: "🔥 Невероятно! 250 анжуманий - можно и пивка ёбнуть, заслужил 🚀",
            500: "🏆 ПОТРЯСАЮЩЕ! 500 анжуманий! царь! 👑\n🎯 МОЧИ ХУЯЧ!",
            1000: "🥇 ЛЕГЕНДАРНО! 1000 анжуманий! Хуя ты мощный! ⚡",
            2500: "🌟 ЭПИЧНО! 2500 анжуманий! Давай Машина мочи 🦾",
            5000: "🔥 ЕБАТЬ! 5000 анжуманий! БОГОПОДОБИЕ! 🤖",
            10000: "👑 Пиздец ты конь! 10000 анжуманий! Вы покорили Олимп! 🏔️"
        }
    },
    'nothing': {
        'table': 'nothin',
        'emoji': '👑',
        'unit': '',
        'name': 'Ни-Че-Го',
        'name_gen': 'ничего',
        'milestones': [100, 250, 500, 1000, 2500, 5000, 10000],
        'messages': {
            100: "ну ок",
            250: "🔥заебись заслужил",
            500: "нууууууу окееееей ",
            1000: "⚡",
            2500: "ты че охуел ничего не делать?",
            5000: "пивка хотябы випей",
            10000: "спасибо Миша!🏔️"
        }
    },
    'beer': {
        'table': 'beer',
        'emoji': '🍺',
        'unit': ' мл.',
        'name': 'Пиво',
        'name_gen': 'мл. пива',
        'milestones': [1000, 2500, 5000, 10000, 25000, 50000],
        'messages': {
            1000: "🍺 Литр пива выпит! Э-э сайпал да давай отжимайся! 😄",
            2500: "🍻 2.5 литра! Время удвоить тренировки! 💪",
            5000: "🍺 5 литров! Серьезные объемы! Баланс - это важно! ⚖️",
            10000: "🍻 10 литров! Вы настоящий ценитель! Не забывайте про спорт! 🏃‍♂️",
            25000: "🍺 25 литров! Впечатляющая статистика! 📊",
            50000: "🍻 50 литров! Легендарный результат! 🏆"
        }
    },
    'bike': {
        'table': 'bike',
        'emoji': '🚲',
        'unit': 'км',
        'name': 'Велосипедик',
        'name_gen': 'км на велике',
        'milestones': [100, 250, 500, 1000, 2500, 5000, 10000],
        'messages': {
            100: "🚲крутышка🚲",
            250: "🔥 крути педали ",
            500: "от Пива не уедешь 🍺🍻🍺",
            1000: "🚀 ИИИХХХУУУ!🎉",
            2500: "🥉 почти до Москвы доехал",
            5000: "🥈 Там уже ноги как столбы!",
            10000: "🥇"
        }
    },
    'pullup': {
        'table': 'pullups',
        'emoji': '🔥',
        'unit': '',
        'name': 'Подтягивания',
        'name_gen': 'Подтягиваний',
        'milestones': [100, 250, 500, 1000, 2500, 5000, 10000],
        'messages': {
            100: " 100 подтягиваний! красаучик 💪",
            250: "🔥 200 подтягиваний!🦾",
            500: "🏆 300 Подтягиваний!!! БОГ! 👑\n🎯 МОЧИ ХУЯЧ!",
            1000: "🥇 ЛЕГЕНДА! 400 Подтягиваний!!! ",
            2500: "ЭПИКККККК!🌟  500 Подтягиваний! Машина 🦾",
            5000: "🔥 ЕБАТЬ! 600 Подтягиваний! БОГОПОДОБИЕ! 🤖",
            10000: "! ну это что-то 10000 Потягушек.! 🏔️"
        }
    },
    # Легко добавить новые активности:
    # 'running': {
    #     'table': 'running',
    #     'emoji': '🏃',
    #     'unit': ' км',
    #     'name': 'Бег',
    #     'name_gen': 'км бега',
    #     'milestones': [10, 25, 50, 100, 250, 500],
    #     'messages': {
    #         10: "🏃 Первые 10 км! Отличное начало!",
    #         25: "🏃‍♂️ 25 км! Вы набираете обороты!",
    #         # и т.д.
    #     }
    # }
}


class FitnessBot:
    def __init__(self):
        self.db_path = os.getenv("DATABASE_PATH", "fitness_bot.db")
        self.init_database()

    def get_week_start_end(self):
        """Получение начала и конца календарной недели"""
        now = datetime.now()
        weekday = now.weekday()

        week_start = now - timedelta(days=weekday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        return week_start, week_end

    def get_moth_start_end(self):
        """Получение начала и конца календарной недели"""
        now = datetime.now()
        weekday = now.weekday()

        week_start = now - timedelta(days=weekday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

        return week_start, week_end

    def init_database(self):
        """Автоматическая инициализация таблиц для всех активностей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Создаем таблицы для всех активностей
        for activity_key, config in ACTIVITIES.items():
            table_name = config['table']
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    count INTEGER NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

        # Таблица достижений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                achievement_type TEXT NOT NULL,
                milestone INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, achievement_type, milestone)
            )
        ''')

        conn.commit()
        conn.close()

    def add_activity(self, activity_type: str, user_id: int, username: str, count: int):
        """Универсальное добавление активности"""
        if activity_type not in ACTIVITIES:
            raise ValueError(f"Неизвестная активность: {activity_type}")

        table_name = ACTIVITIES[activity_type]['table']

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO {table_name} (user_id, username, count) VALUES (?, ?, ?)",
            (user_id, username, count)
        )
        conn.commit()
        conn.close()

    def get_activity_stats(self, activity_type: str, user_id: int):
        """Получение статистики по одной активности"""
        if activity_type not in ACTIVITIES:
            return {'today': 0, 'week': 0, 'total': 0}

        table_name = ACTIVITIES[activity_type]['table']
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        week_start, week_end = self.get_week_start_end()

        # За сегодня
        cursor.execute(f"""
            SELECT SUM(count) FROM {table_name} 
            WHERE user_id = ? AND DATE(timestamp) = DATE('now')
        """, (user_id,))
        today = cursor.fetchone()[0] or 0

        # За неделю
        cursor.execute(f"""
            SELECT SUM(count) FROM {table_name} 
            WHERE user_id = ? AND timestamp >= ? AND timestamp <= ?
        """, (user_id, week_start, week_end))
        week = cursor.fetchone()[0] or 0

        # Всего
        cursor.execute(f"""
            SELECT SUM(count) FROM {table_name} WHERE user_id = ?
        """, (user_id,))
        total = cursor.fetchone()[0] or 0

        conn.close()
        return {'today': today, 'week': week, 'total': total}

    def get_user_stats(self, user_id: int):
        """Получение статистики пользователя по всем активностям"""
        stats = {}
        for activity_key in ACTIVITIES:
            stats[activity_key] = self.get_activity_stats(activity_key, user_id)
        return stats

    def check_and_add_achievement(self, user_id: int, username: str, activity_type: str, current_total: int):
        """Проверка и добавление достижения"""
        if activity_type not in ACTIVITIES:
            return []

        milestones = ACTIVITIES[activity_type]['milestones']

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        new_achievements = []
        for milestone in milestones:
            if current_total >= milestone:
                try:
                    cursor.execute(
                        "INSERT INTO achievements (user_id, username, achievement_type, milestone) VALUES (?, ?, ?, ?)",
                        (user_id, username, activity_type, milestone)
                    )
                    new_achievements.append(milestone)
                except sqlite3.IntegrityError:
                    continue

        conn.commit()
        conn.close()
        return new_achievements

    def get_achievement_message(self, activity_type: str, milestone: int):
        """Получение сообщения о достижении"""
        if activity_type not in ACTIVITIES:
            return f"🎉 Достижение: {milestone} {activity_type}!"

        messages = ACTIVITIES[activity_type]['messages']
        return messages.get(milestone, f"🎉 Достижение разблокировано: {milestone} {activity_type}!")

    def get_all_users_stats(self):
        """Получение статистики всех пользователей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Собираем всех пользователей из всех таблиц
        union_queries = []
        for config in ACTIVITIES.values():
            union_queries.append(f"SELECT user_id, username FROM {config['table']}")

        union_query = " UNION ".join(union_queries)

        cursor.execute(f"""
            SELECT DISTINCT user_id, username FROM ({union_query})
        """)
        users = cursor.fetchall()

        stats = []
        for user_id, username in users:
            user_stats = self.get_user_stats(user_id)
            stats.append({
                'user_id': user_id,
                'username': username or f"ID{user_id}",
                'stats': user_stats
            })

        conn.close()
        return stats

    def format_stats_message(self, stats, title="📊 Статистика"):
        """Форматирование сообщения со статистикой"""
        message = f"{title}:\n\n"

        for activity_key, activity_stats in stats.items():
            config = ACTIVITIES[activity_key]
            emoji = config['emoji']
            name = config['name']
            unit = config['unit']

            message += f"{emoji} {name}:\n"
            message += f"  • Сегодня: {activity_stats['today']}{unit}\n"
            message += f"  • За неделю: {activity_stats['week']}{unit}\n"
            message += f"  • Всего: {activity_stats['total']}{unit}\n\n"

        message += "📅 Неделя: с понедельника по воскресенье"
        return message


# Создаем экземпляр бота
bot = FitnessBot()


def create_activity_handler(activity_type: str):
    """Фабрика для создания обработчиков команд активностей"""
    config = ACTIVITIES[activity_type]

    async def activity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not context.args:
                await update.message.reply_text(
                    f"❌ Укажите количество {config['name_gen']}!\nПример: /{activity_type} 50")
                return

            count = int(context.args[0])
            if count < 0:
                await update.message.reply_text("❌ Количество не может быть отрицательным!")
                return
            if count == 0:
                await update.message.reply_text("❌ Количество должно быть больше нуля!")
                return
            if count > 10000:
                await update.message.reply_text("❌ Слишком большое число! Максимум 10000 за раз.")
                return

            user_id = update.effective_user.id
            username = update.effective_user.username

            bot.add_activity(activity_type, user_id, username, count)
            stats = bot.get_user_stats(user_id)
            new_achievements = bot.check_and_add_achievement(
                user_id, username, activity_type, stats[activity_type]['total']
            )

            # Формируем краткое сообщение с текущей статистикой
            response = f"✅ Записано {count} {config['name_gen']}!\n\n"

            # Добавляем краткую статистику
            response += "📊 Сегодня | За неделю:\n"
            for act_key, act_stats in stats.items():
                act_config = ACTIVITIES[act_key]
                response += f"{act_config['emoji']} {act_config['name']}: {act_stats['today']} | {act_stats['week']}{act_config['unit']}\n"

            await update.message.reply_text(response)

            # Отправляем сообщения о достижениях
            for achievement in new_achievements:
                achievement_message = bot.get_achievement_message(activity_type, achievement)
                await update.message.reply_text(achievement_message)

        except ValueError:
            await update.message.reply_text(f"❌ Неверный формат! Введите число.\nПример: /{activity_type} 50")
        except Exception as e:
            logger.error(f"Error in {activity_type}_command: {e}")
            await update.message.reply_text("❌ Произошла ошибка при записи данных.")

    return activity_handler


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    commands_list = []
    for activity_key, config in ACTIVITIES.items():
        commands_list.append(f"• /{activity_key} <число> - записать {config['name_gen']}")

    welcome_text = f"""
🏋️ Добро пожаловать в Супер-бот!

Доступные команды:
{chr(10).join(commands_list)}
• /stats - моя статистика
• /total - статистика всех пользователей

🏆 Система достижений активна для всех активностей!

📅 Статистика за неделю считается с понедельника по воскресенье

Пример: /pushup 50
    """
    await update.message.reply_text(welcome_text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats"""
    try:
        user_id = update.effective_user.id
        stats = bot.get_user_stats(user_id)
        response = bot.format_stats_message(stats, "📊 Ваша статистика")
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении статистики.")


async def total_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /total"""
    try:
        all_stats = bot.get_all_users_stats()
        if not all_stats:
            await update.message.reply_text("📊 Пока нет данных для отображения статистики.")
            return

        response = "📊 Общая статистика всех пользователей:\n📅 Неделя: с понедельника по воскресенье\n\n"

        # Сортируем по отжиманиям (можно изменить критерий)
        all_stats.sort(key=lambda x: x['stats']['pushup']['total'], reverse=True)

        for i, user_data in enumerate(all_stats, 1):
            username = user_data['username']
            stats = user_data['stats']

            response += f"{i}. @{username}\n"
            for activity_key, activity_stats in stats.items():
                config = ACTIVITIES[activity_key]
                response += f"   {config['emoji']} {config['name']}: {activity_stats['total']} (неделя: {activity_stats['week']}, сегодня: {activity_stats['today']}){config['unit']}\n"
            response += "\n"

        # Разбиваем длинное сообщение
        if len(response) > 4096:
            parts = [response[i:i + 4096] for i in range(0, len(response), 4096)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error in total_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении статистики.")


async def handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка неизвестных команд"""
    command = update.message.text.strip()

    if command == "/":
        await update.message.reply_text("❌ Пустая команда! Используйте /start для просмотра доступных команд.")
        return

    # Проверяем команды активностей без аргументов
    for activity_key, config in ACTIVITIES.items():
        if command == f"/{activity_key}":
            await update.message.reply_text(f"❌ Укажите количество {config['name_gen']}!\nПример: /{activity_key} 50")
            return

    # Список доступных команд
    commands_list = []
    for activity_key, config in ACTIVITIES.items():
        commands_list.append(f"• /{activity_key} <число> - записать {config['name_gen']}")

    await update.message.reply_text(
        f"❌ Неизвестная команда: {command}\n\n"
        f"Доступные команды:\n{chr(10).join(commands_list)}\n"
        "• /stats - моя статистика\n"
        "• /total - общая статистика\n"
        "• /start - справка"
    )


def main():
    """Основная функция запуска бота"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()

        # Базовые команды
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("total", total_command))

        # Автоматически создаем обработчики для всех активностей
        for activity_key in ACTIVITIES:
            handler = create_activity_handler(activity_key)
            application.add_handler(CommandHandler(activity_key, handler))

        # Обработчик неизвестных команд
        application.add_handler(MessageHandler(filters.COMMAND, handle_unknown_command))

        logger.info("🤖 Фитнес-бот запущен и работает!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Критическая ошибка запуска бота: {e}")
        raise


if __name__ == '__main__':
    main()