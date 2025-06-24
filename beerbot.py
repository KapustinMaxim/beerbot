import logging
import sqlite3
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import asyncio
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования для Railway
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]  # Только консольный вывод для Railway
)
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")


class FitnessBot:
    def __init__(self):
        self.init_database()

    def init_database(self):
        """Инициализация базы данных SQLite"""
        # Путь к базе данных
        db_path = os.getenv("DATABASE_PATH", "fitness_bot.db")

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Создание таблицы для отжиманий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pushups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                count INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создание таблицы для мл. пива
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS beer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                count INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создание таблицы для достижений
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

    def add_pushups(self, user_id: int, username: str, count: int):
        """Добавление записи об отжиманиях"""
        db_path = os.getenv("DATABASE_PATH", "fitness_bot.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pushups (user_id, username, count) VALUES (?, ?, ?)",
            (user_id, username, count)
        )
        conn.commit()
        conn.close()

    def add_beer(self, user_id: int, username: str, count: int):
        """Добавление записи о пиве"""
        db_path = os.getenv("DATABASE_PATH", "fitness_bot.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO beer (user_id, username, count) VALUES (?, ?, ?)",
            (user_id, username, count)
        )
        conn.commit()
        conn.close()

    def check_and_add_achievement(self, user_id: int, username: str, achievement_type: str, current_total: int):
        """Проверка и добавление достижения"""
        db_path = os.getenv("DATABASE_PATH", "fitness_bot.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Определяем пороги достижений
        milestones = {
            'pushups': [100, 250, 500, 1000, 2500, 5000, 10000],
            'beer': [1000, 2500, 5000, 10000, 25000, 50000]  # в мл
        }

        if achievement_type not in milestones:
            conn.close()
            return []

        new_achievements = []

        for milestone in milestones[achievement_type]:
            if current_total >= milestone:
                try:
                    cursor.execute(
                        "INSERT INTO achievements (user_id, username, achievement_type, milestone) VALUES (?, ?, ?, ?)",
                        (user_id, username, achievement_type, milestone)
                    )
                    new_achievements.append(milestone)
                except sqlite3.IntegrityError:
                    # Достижение уже существует
                    continue

        conn.commit()
        conn.close()
        return new_achievements

    def get_achievement_message(self, achievement_type: str, milestone: int):
        """Получение сообщения о достижении"""
        messages = {
            'pushups': {
                100: "🎉 Поздравляем! Вы достигли 100 отжиманий! Отличное начало! 💪",
                250: "🔥 Невероятно! 250 отжиманий - вы на правильном пути! 🚀",
                500: "🏆 ПОТРЯСАЮЩЕ! 500 отжиманий! Вы настоящий чемпион! 👑\n🎯 МОЧИ ХУЯЧ!",
                1000: "🥇 ЛЕГЕНДАРНО! 1000 отжиманий! Хуя ты мощный! ⚡",
                2500: "🌟 ЭПИЧНО! 2500 отжиманий! Давай Машина мочи 🦾",
                5000: "🔥 ЕБАТЬ! 5000 отжиманий! БОГОПОДОБИЕ! 🤖",
                10000: "👑 Пиздец ты конь! 10000 отжиманий! Вы покорили Олимп! 🏔️"
            },
            'beer': {
                1000: "🍺 Литр пива выпит! ЗАИПАЛ давай отжимайся! 😄",
                2500: "🍻 2.5 литра! Время удвоить тренировки! 💪",
                5000: "🍺 5 литров! Серьезные объемы! Баланс - это важно! ⚖️",
                10000: "🍻 10 литров! Вы настоящий ценитель! Не забывайте про спорт! 🏃‍♂️",
                25000: "🍺 25 литров! Впечатляющая статистика! 📊",
                50000: "🍻 50 литров! Легендарный результат! 🏆"
            }
        }

        return messages.get(achievement_type, {}).get(milestone,
                                                      f"🎉 Достижение разблокировано: {milestone} {achievement_type}!")

    def get_user_stats(self, user_id: int):
        """Получение статистики пользователя"""
        db_path = os.getenv("DATABASE_PATH", "fitness_bot.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        now = datetime.now()
        today = now.date()
        week_ago = now - timedelta(days=7)

        # Отжимания
        # За сегодня
        cursor.execute("""
            SELECT SUM(count) FROM pushups 
            WHERE user_id = ? AND DATE(timestamp) = DATE('now')
        """, (user_id,))
        pushups_today = cursor.fetchone()[0] or 0

        # За неделю
        cursor.execute("""
            SELECT SUM(count) FROM pushups 
            WHERE user_id = ? AND timestamp >= ?
        """, (user_id, week_ago))
        pushups_week = cursor.fetchone()[0] or 0

        # Всего
        cursor.execute("""
            SELECT SUM(count) FROM pushups WHERE user_id = ?
        """, (user_id,))
        pushups_total = cursor.fetchone()[0] or 0

        # Пиво
        # За сегодня
        cursor.execute("""
            SELECT SUM(count) FROM beer 
            WHERE user_id = ? AND DATE(timestamp) = DATE('now')
        """, (user_id,))
        beer_today = cursor.fetchone()[0] or 0

        # За неделю
        cursor.execute("""
            SELECT SUM(count) FROM beer 
            WHERE user_id = ? AND timestamp >= ?
        """, (user_id, week_ago))
        beer_week = cursor.fetchone()[0] or 0

        # Всего
        cursor.execute("""
            SELECT SUM(count) FROM beer WHERE user_id = ?
        """, (user_id,))
        beer_total = cursor.fetchone()[0] or 0

        conn.close()

        return {
            'pushups': {'today': pushups_today, 'week': pushups_week, 'total': pushups_total},
            'beer': {'today': beer_today, 'week': beer_week, 'total': beer_total}
        }

    def get_all_users_stats(self):
        """Получение статистики всех пользователей"""
        db_path = os.getenv("DATABASE_PATH", "fitness_bot.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Получаем всех пользователей
        cursor.execute("""
            SELECT DISTINCT user_id, username FROM (
                SELECT user_id, username FROM pushups
                UNION
                SELECT user_id, username FROM beer
            )
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


# Создаем экземпляр бота
bot = FitnessBot()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    welcome_text = """
🏋️ Добро пожаловать в фитнес-бот!

Доступные команды:
• /pushup <число> - записать отжимания
• /beer <число> - записать количество мл. пива
• /stats - моя статистика
• /total - статистика всех пользователей

🏆 Система достижений:
• 100, 250, 500, 1000, 2500, 5000, 10000 отжиманий
• Особые награды за важные рубежи!

Пример: /pushup 50
    """
    await update.message.reply_text(welcome_text)


async def pushup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /pushup для записи отжиманий"""
    try:
        if not context.args:
            await update.message.reply_text("❌ Укажите количество отжиманий!\nПример: /pushup 50")
            return

        count = int(context.args[0])
        if count < 0:
            await update.message.reply_text("❌ Количество не может быть отрицательным числом!")
            return
        if count == 0:
            await update.message.reply_text("❌ Количество должно быть больше нуля!")
            return
        if count > 10000:
            await update.message.reply_text("❌ Слишком большое число! Максимум 10000 за раз.")
            return

        user_id = update.effective_user.id
        username = update.effective_user.username

        bot.add_pushups(user_id, username, count)

        # Получаем обновленную статистику
        stats = bot.get_user_stats(user_id)

        # Проверяем достижения
        new_achievements = bot.check_and_add_achievement(user_id, username, 'pushups', stats['pushups']['total'])

        response = f"""
✅ Записано {count} отжиманий!

📊 Статистика за день и неделю:
🔥 Отжимания: {stats['pushups']['today']} сегодня | {stats['pushups']['week']} за неделю
🍺 Пиво: {stats['beer']['today']} мл. сегодня | {stats['beer']['week']} мл. за неделю
        """

        await update.message.reply_text(response)

        # Отправляем сообщения о новых достижениях
        for achievement in new_achievements:
            achievement_message = bot.get_achievement_message('pushups', achievement)
            await update.message.reply_text(achievement_message)

    except ValueError:
        await update.message.reply_text("❌ Неверный формат! Введите число.\nПример: /pushup 50")
    except Exception as e:
        logger.error(f"Error in pushup_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка при записи данных.")


async def beer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /beer для записи мл. мл. пива"""
    try:
        if not context.args:
            await update.message.reply_text("❌ Укажите количество мл. пива!\nПример: /beer 2")
            return

        count = int(context.args[0])
        if count < 0:
            await update.message.reply_text("❌ Количество мл. не может быть отрицательным числом!")
            return
        if count == 0:
            await update.message.reply_text("❌ Количество мл. должно быть больше нуля!")
            return
        if count > 10000:
            await update.message.reply_text("❌ Слишком много мл. пива! Максимум 10 л. за раз.")
            return

        user_id = update.effective_user.id
        username = update.effective_user.username

        bot.add_beer(user_id, username, count)

        # Получаем обновленную статистику
        stats = bot.get_user_stats(user_id)

        # Проверяем достижения
        new_achievements = bot.check_and_add_achievement(user_id, username, 'beer', stats['beer']['total'])

        response = f"""
✅ Записано {count} мл. пива!

📊 Статистика за день и неделю:
🔥 Отжимания: {stats['pushups']['today']} сегодня | {stats['pushups']['week']} за неделю
🍺 Пиво: {stats['beer']['today']} мл. сегодня | {stats['beer']['week']} мл. за неделю
        """

        await update.message.reply_text(response)

        # Отправляем сообщения о новых достижениях
        for achievement in new_achievements:
            achievement_message = bot.get_achievement_message('beer', achievement)
            await update.message.reply_text(achievement_message)

    except ValueError:
        await update.message.reply_text("❌ Неверный формат! Введите число.\nПример: /beer 2")
    except Exception as e:
        logger.error(f"Error in beer_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка при записи данных.")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats для показа личной статистики"""
    try:
        user_id = update.effective_user.id
        stats = bot.get_user_stats(user_id)

        response = f"""
📊 Ваша статистика:

🔥 Отжимания:
  • Сегодня: {stats['pushups']['today']}
  • За неделю: {stats['pushups']['week']}
  • Всего: {stats['pushups']['total']}

🍺 Пиво:
  • Сегодня: {stats['beer']['today']} мл.
  • За неделю: {stats['beer']['week']} мл.
  • Всего: {stats['beer']['total']} мл.
        """

        await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении статистики.")


async def total_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /total для показа статистики всех пользователей"""
    try:
        all_stats = bot.get_all_users_stats()

        if not all_stats:
            await update.message.reply_text("📊 Пока нет данных для отображения статистики.")
            return

        response = "📊 Общая статистика всех пользователей:\n\n"

        # Сортируем по общему количеству отжиманий
        all_stats.sort(key=lambda x: x['stats']['pushups']['total'], reverse=True)

        for i, user_data in enumerate(all_stats, 1):
            username = user_data['username']
            stats = user_data['stats']

            response += f"{i}. @{username}\n"
            response += f"   🔥 Отжимания: {stats['pushups']['total']} (неделя: {stats['pushups']['week']}, сегодня: {stats['pushups']['today']})\n"
            response += f"   🍺 Пиво: {stats['beer']['total']} мл. (неделя: {stats['beer']['week']} мл., сегодня: {stats['beer']['today']} мл.)\n\n"

        # Разбиваем длинное сообщение на части, если необходимо
        if len(response) > 4096:
            parts = [response[i:i + 4096] for i in range(0, len(response), 4096)]
            for part in parts:
                await update.message.reply_text(part)
        else:
            await update.message.reply_text(response)

    except Exception as e:
        logger.error(f"Error in total_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении общей статистики.")


async def handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка неизвестных команд"""
    command = update.message.text

    # Проверяем, не пустая ли команда после /
    if command.strip() == "/":
        await update.message.reply_text("❌ Пустая команда! Используйте /start для просмотра доступных команд.")
        return

    # Проверяем команды без аргументов
    if command.strip() in ["/pushup", "/beer"]:
        if command.strip() == "/pushup":
            await update.message.reply_text("❌ Укажите количество отжиманий!\nПример: /pushup 50")
        elif command.strip() == "/beer":
            await update.message.reply_text("❌ Укажите количество мл. пива!\nПример: /beer 2")
        return

    # Для всех остальных неизвестных команд
    await update.message.reply_text(
        f"❌ Неизвестная команда: {command}\n\n"
        "Доступные команды:\n"
        "• /pushup <число> - записать отжимания\n"
        "• /beer <число> - записать пиво\n"
        "• /stats - моя статистика\n"
        "• /total - общая статистика\n"
        "• /start - справка"
    )


def main():
    """Основная функция запуска бота"""
    try:
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("pushup", pushup_command))
        application.add_handler(CommandHandler("beer", beer_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("total", total_command))

        # Обработчик неизвестных команд (должен быть последним)
        application.add_handler(MessageHandler(filters.COMMAND, handle_unknown_command))

        # Запускаем бота
        logger.info("🤖 Фитнес-бот запущен и работает на Railway!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Критическая ошибка запуска бота: {e}")
        raise


if __name__ == '__main__':
    main()