import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import sqlite3
import datetime
import random
import time
from typing import Dict, List, Tuple, Optional
from telegram import MessageEntity
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def create_user_mention(user_id: int, user_name: str) -> str:
    """Создает кликабельное упоминание пользователя"""
    return f'<a href="tg://user?id={user_id}">{user_name}</a>'

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Таблица браков
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marriages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER,
            user1_name TEXT,
            user2_id INTEGER,
            user2_name TEXT,
            marriage_date TEXT,
            divorce_date TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Таблица предложений брака
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS marriage_proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user_id INTEGER,
            from_user_name TEXT,
            to_user_id INTEGER,
            to_user_name TEXT,
            message_id INTEGER,
            timestamp TEXT
        )
    ''')
    
    # Таблица детей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent1_id INTEGER,
            parent2_id INTEGER,
            name TEXT,
            age INTEGER DEFAULT 0,
            created_date TEXT
        )
    ''')
    
    # Таблица похищений
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kidnappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kidnapper_id INTEGER,
            kidnapper_name TEXT,
            victim_id INTEGER,
            victim_name TEXT,
            kidnap_time TEXT,
            duration_hours INTEGER DEFAULT 6
        )
    ''')
    
    # Таблица краж для топа
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kidnap_stats (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT,
            kidnap_count INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица ссор
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS arguments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER,
            user2_id INTEGER,
            start_time TEXT,
            duration_hours INTEGER DEFAULT 24
        )
    ''')
    
    # Таблица последних команд
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cooldowns (
            user_id INTEGER PRIMARY KEY,
            command TEXT,
            last_used TEXT
        )
    ''')
    
    # Таблица имен детей (в процессе выбора)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS child_naming (
            user_id INTEGER PRIMARY KEY,
            child_id INTEGER,
            temp_name TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Функции для работы с базой данных

def get_marriage_by_users(user1_name: str, user2_name: str) -> Dict:
    """Получает информацию о браке по именам пользователей"""
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM marriages 
        WHERE (user1_name = ? AND user2_name = ?) OR (user1_name = ? AND user2_name = ?)
        AND is_active = 1
    ''', (user1_name, user2_name, user2_name, user1_name))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'user1_id': result[1],
            'user1_name': result[2],
            'user2_id': result[3],
            'user2_name': result[4],
            'marriage_date': result[5],
            'divorce_date': result[6],
            'is_active': result[7]
        }
    return None

def get_user_id_by_name(user_name: str) -> Optional[int]:
    """Получает ID пользователя по имени из любой таблицы"""
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Пробуем найти в таблице браков
    cursor.execute('SELECT user1_id FROM marriages WHERE user1_name = ? LIMIT 1', (user_name,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return result[0]
    
    # Пробуем найти в таблице похищений
    cursor.execute('SELECT kidnapper_id FROM kidnappings WHERE kidnapper_name = ? LIMIT 1', (user_name,))
    result = cursor.fetchone()
    if result:
        conn.close()
        return result[0]
    
    # Пробуем найти в статистике похищений
    cursor.execute('SELECT user_id FROM kidnap_stats WHERE user_name = ? LIMIT 1', (user_name,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def get_marriage(user_id: int) -> Dict:
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM marriages 
        WHERE (user1_id = ? OR user2_id = ?) AND is_active = 1
    ''', (user_id, user_id))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'user1_id': result[1],
            'user1_name': result[2],
            'user2_id': result[3],
            'user2_name': result[4],
            'marriage_date': result[5],
            'divorce_date': result[6],
            'is_active': result[7]
        }
    return None

def create_marriage(user1_id: int, user1_name: str, user2_id: int, user2_name: str):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    marriage_date = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO marriages (user1_id, user1_name, user2_id, user2_name, marriage_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (user1_id, user1_name, user2_id, user2_name, marriage_date))
    
    conn.commit()
    conn.close()

def divorce_marriage(marriage_id: int):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    divorce_date = datetime.datetime.now().isoformat()
    cursor.execute('''
        UPDATE marriages 
        SET is_active = 0, divorce_date = ?
        WHERE id = ?
    ''', (divorce_date, marriage_id))
    
    conn.commit()
    conn.close()

def get_marriage_days(marriage_date: str) -> int:
    marriage_dt = datetime.datetime.fromisoformat(marriage_date)
    now = datetime.datetime.now()
    return (now - marriage_dt).days

def get_top_marriages() -> List[Tuple]:
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user1_name, user2_name, marriage_date 
        FROM marriages 
        WHERE is_active = 1 
        ORDER BY marriage_date ASC 
        LIMIT 10
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    return results

def save_proposal(from_user_id: int, from_user_name: str, to_user_id: int, to_user_name: str, message_id: int):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    timestamp = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO marriage_proposals (from_user_id, from_user_name, to_user_id, to_user_name, message_id, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (from_user_id, from_user_name, to_user_id, to_user_name, message_id, timestamp))
    
    conn.commit()
    conn.close()

def get_proposal_by_message(message_id: int) -> Dict:
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM marriage_proposals WHERE message_id = ?', (message_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'from_user_id': result[1],
            'from_user_name': result[2],
            'to_user_id': result[3],
            'to_user_name': result[4],
            'message_id': result[5],
            'timestamp': result[6]
        }
    return None

def delete_proposal(proposal_id: int):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM marriage_proposals WHERE id = ?', (proposal_id,))
    conn.commit()
    conn.close()

# Функции для ссор
def create_argument(user1_id: int, user2_id: int):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    start_time = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO arguments (user1_id, user2_id, start_time)
        VALUES (?, ?, ?)
    ''', (user1_id, user2_id, start_time))
    
    conn.commit()
    conn.close()

def get_argument(user_id: int) -> Dict:
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM arguments 
        WHERE (user1_id = ? OR user2_id = ?) 
        AND datetime(start_time) > datetime('now', '-' || duration_hours || ' hours')
    ''', (user_id, user_id))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'user1_id': result[1],
            'user2_id': result[2],
            'start_time': result[3],
            'duration_hours': result[4]
        }
    return None

def delete_argument(argument_id: int):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM arguments WHERE id = ?', (argument_id,))
    conn.commit()
    conn.close()

# Функции для детей
def create_child(parent1_id: int, parent2_id: int):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    created_date = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO children (parent1_id, parent2_id, created_date)
        VALUES (?, ?, ?)
    ''', (parent1_id, parent2_id, created_date))
    
    child_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return child_id

def get_children(parent_id: int) -> List[Dict]:
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM children 
        WHERE parent1_id = ? OR parent2_id = ?
        ORDER BY created_date
    ''', (parent_id, parent_id))
    
    results = cursor.fetchall()
    conn.close()
    
    children = []
    for result in results:
        children.append({
            'id': result[0],
            'parent1_id': result[1],
            'parent2_id': result[2],
            'name': result[3],
            'age': result[4],
            'created_date': result[5]
        })
    return children

def update_child_name(child_id: int, name: str):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE children SET name = ? WHERE id = ?', (name, child_id))
    conn.commit()
    conn.close()

def increase_child_age(child_id: int):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE children SET age = age + 1 WHERE id = ?', (child_id,))
    conn.commit()
    conn.close()

def increase_all_children_age(parent_id: int):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE children 
        SET age = age + 1 
        WHERE parent1_id = ? OR parent2_id = ?
    ''', (parent_id, parent_id))
    
    conn.commit()
    conn.close()

def delete_child(child_id: int):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM children WHERE id = ?', (child_id,))
    conn.commit()
    conn.close()

# Функции для имен детей
def save_temp_name(user_id: int, child_id: int, temp_name: str):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO child_naming (user_id, child_id, temp_name)
        VALUES (?, ?, ?)
    ''', (user_id, child_id, temp_name))
    
    conn.commit()
    conn.close()

def get_temp_name(user_id: int) -> Dict:
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM child_naming WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'user_id': result[0],
            'child_id': result[1],
            'temp_name': result[2]
        }
    return None

def delete_temp_name(user_id: int):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM child_naming WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# Функции для кражи
def get_kidnap_info(kidnapper_id: int) -> Dict:
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM kidnappings 
        WHERE kidnapper_id = ?
    ''', (kidnapper_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'kidnapper_id': result[1],
            'kidnapper_name': result[2],
            'victim_id': result[3],
            'victim_name': result[4],
            'kidnap_time': result[5],
            'duration_hours': result[6]
        }
    return None

def get_kidnap_victim_info(victim_id: int) -> Dict:
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM kidnappings 
        WHERE victim_id = ?
    ''', (victim_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            'id': result[0],
            'kidnapper_id': result[1],
            'kidnapper_name': result[2],
            'victim_id': result[3],
            'victim_name': result[4],
            'kidnap_time': result[5],
            'duration_hours': result[6]
        }
    return None

def can_kidnap(user_id: int) -> Tuple[bool, int]:
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('SELECT last_used FROM cooldowns WHERE user_id = ? AND command = ?', 
                  (user_id, 'kidnap'))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return True, 0
    
    last_used = datetime.datetime.fromisoformat(result[0])
    now = datetime.datetime.now()
    cooldown = datetime.timedelta(minutes=15)
    
    if now - last_used < cooldown:
        remaining = cooldown - (now - last_used)
        return False, int(remaining.total_seconds() // 60)
    
    return True, 0

def update_cooldown(user_id: int, command: str):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    now = datetime.datetime.now().isoformat()
    cursor.execute('''
        INSERT OR REPLACE INTO cooldowns (user_id, command, last_used)
        VALUES (?, ?, ?)
    ''', (user_id, command, now))
    
    conn.commit()
    conn.close()

def delete_kidnap(kidnap_id: int):
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM kidnappings WHERE id = ?', (kidnap_id,))
    conn.commit()
    conn.close()

def get_top_kidnappers() -> List[Tuple]:
    conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_name, kidnap_count 
        FROM kidnap_stats 
        ORDER BY kidnap_count DESC 
        LIMIT 10
    ''')
    
    results = cursor.fetchall()
    conn.close()
    
    return results

# Команды брака
# Обнови функцию propose для кликабельных ников
async def propose(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Пожалуйста, ответьте на сообщение человека, с которым хотите заключить брак!")
        return
    
    from_user = update.message.from_user
    to_user = update.message.reply_to_message.from_user
    
    if from_user.id == to_user.id:
        await update.message.reply_text("Вы не можете заключить брак с самим собой!")
        return
    
    # Проверяем, не состоит ли уже кто-то в браке
    existing_marriage = get_marriage(from_user.id)
    if existing_marriage:
        await update.message.reply_text("Вы уже состоите в браке!")
        return
    
    existing_marriage = get_marriage(to_user.id)
    if existing_marriage:
        await update.message.reply_text("Этот пользователь уже состоит в браке!")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data=f"propose_yes_{from_user.id}_{to_user.id}"),
            InlineKeyboardButton("Нет", callback_data=f"propose_no_{from_user.id}_{to_user.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Используем универсальную функцию для кликабельных ников
    from_user_mention = create_user_mention(from_user.id, from_user.first_name)
    to_user_mention = create_user_mention(to_user.id, to_user.first_name)
    
    message = await update.message.reply_text(
        f"{from_user_mention} предлагает {to_user_mention} вступить в брак! Согласны ли вы?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    save_proposal(from_user.id, from_user.first_name, to_user.id, to_user.first_name, message.message_id)

# Обнови функцию handle_propose_response для кликабельных ников
async def handle_propose_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    response = data[1]
    from_user_id = int(data[2])
    to_user_id = int(data[3])
    
    proposal = get_proposal_by_message(query.message.message_id)
    if not proposal:
        await query.edit_message_text("Предложение не найдено или устарело")
        return
    
    # Используем универсальную функцию для кликабельных ников
    from_user_mention = create_user_mention(proposal["from_user_id"], proposal["from_user_name"])
    to_user_mention = create_user_mention(proposal["to_user_id"], proposal["to_user_name"])
    
    if response == 'yes':
        create_marriage(proposal['from_user_id'], proposal['from_user_name'], 
                       proposal['to_user_id'], proposal['to_user_name'])
        
        await query.edit_message_text(
            f"С сегодняшнего дня {from_user_mention} и {to_user_mention} "
            f"состоят в браке и начинается отсчёт количества дней нахождения в браке",
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text(
            f"Сожалеем {from_user_mention}, {to_user_mention} "
            f"отклонил(а) ваше предложение",
            parse_mode='HTML'
        )
    
    delete_proposal(proposal['id'])

async def marriage_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    marriage = get_marriage(user.id)
    
    if not marriage:
        await update.message.reply_text("Вы не состоите в браке")
        return
    
    days = get_marriage_days(marriage['marriage_date'])
    
    # Используем универсальную функцию для кликабельных ников
    user1_mention = create_user_mention(marriage["user1_id"], marriage["user1_name"])
    user2_mention = create_user_mention(marriage["user2_id"], marriage["user2_name"])
    
    await update.message.reply_text(
        f"{user1_mention} и {user2_mention} в браке уже {days} дней",
        parse_mode='HTML'
    )

async def divorce_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    marriage = get_marriage(user.id)
    
    if not marriage:
        await update.message.reply_text("Вы не состоите в браке")
        return
    
    partner_id = marriage['user2_id'] if marriage['user1_id'] == user.id else marriage['user1_id']
    partner_name = marriage['user2_name'] if marriage['user1_id'] == user.id else marriage['user1_name']
    
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data=f"divorce_yes_{marriage['id']}"),
            InlineKeyboardButton("Нет", callback_data=f"divorce_no_{marriage['id']}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Используем универсальную функцию для кликабельных ников
    partner_mention = create_user_mention(partner_id, partner_name)
    
    await update.message.reply_text(
        f"Вы уверены что хотите развестись с {partner_mention}?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def handle_divorce_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    response = data[1]
    marriage_id = int(data[2])
    
    marriage = get_marriage(query.from_user.id)
    if not marriage or marriage['id'] != marriage_id:
        await query.edit_message_text("Брак не найден")
        return
    
    # Используем универсальную функцию для кликабельных ников
    user1_mention = create_user_mention(marriage["user1_id"], marriage["user1_name"])
    user2_mention = create_user_mention(marriage["user2_id"], marriage["user2_name"])
    
    if response == 'yes':
        divorce_marriage(marriage_id)
        days = get_marriage_days(marriage['marriage_date'])
        
        await query.edit_message_text(
            f"С сегодняшнего дня {user1_mention} и {user2_mention} "
            f"не состоят в браке. Брак продлился {days} дней",
            parse_mode='HTML'
        )
    else:
        await query.delete_message()

async def marriages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_marriages = get_top_marriages()
    
    if not top_marriages:
        await update.message.reply_text("Пока нет активных браков")
        return
    
    text = "🏆 Топ самых долгих браков:\n\n"
    for i, marriage in enumerate(top_marriages, 1):
        days = get_marriage_days(marriage[2])
        
        # Получаем ID пользователей из базы данных
        marriage_info = get_marriage_by_users(marriage[0], marriage[1])
        if marriage_info:
            user1_mention = create_user_mention(marriage_info['user1_id'], marriage[0])
            user2_mention = create_user_mention(marriage_info['user2_id'], marriage[1])
            text += f"{i}. {user1_mention} и {user2_mention} - {days} дней\n"
        else:
            text += f"{i}. {marriage[0]} и {marriage[1]} - {days} дней\n"
    
    await update.message.reply_text(text, parse_mode='HTML')

async def argue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    marriage = get_marriage(user.id)
    
    if not marriage:
        await update.message.reply_text("Вы не состоите в браке!")
        return
    
    partner_id = marriage['user2_id'] if marriage['user1_id'] == user.id else marriage['user1_id']
    partner_name = marriage['user2_name'] if marriage['user1_id'] == user.id else marriage['user1_name']
    
    # Проверяем, нет ли активной ссоры
    existing_argument = get_argument(user.id)
    if existing_argument:
        await update.message.reply_text("Вы уже в ссоре!")
        return
    
    create_argument(user.id, partner_id)
    
    # Используем универсальную функцию для кликабельных ников
    user_mention = create_user_mention(user.id, user.first_name)
    partner_mention = create_user_mention(partner_id, partner_name)
    
    await update.message.reply_text(
        f"{user_mention} поссорился с {partner_mention} на 1 день",
        parse_mode='HTML'
    )

async def make_peace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    argument = get_argument(user.id)
    
    if not argument:
        await update.message.reply_text("Вы не в ссоре!")
        return
    
    delete_argument(argument['id'])
    
    # Получаем имя партнера из брака
    marriage = get_marriage(user.id)
    if marriage:
        partner_id = marriage['user2_id'] if marriage['user1_id'] == user.id else marriage['user1_id']
        partner_name = marriage['user2_name'] if marriage['user1_id'] == user.id else marriage['user1_name']
        
        # Используем универсальную функцию для кликабельных ников
        user_mention = create_user_mention(user.id, user.first_name)
        partner_mention = create_user_mention(partner_id, partner_name)
        
        await update.message.reply_text(
            f"{user_mention} помирился с {partner_mention}",
            parse_mode='HTML'
        )

# Взаимодействия - создаем латинские команды для взаимодействий
INTERACTION_COMMANDS = {
    'hug': 'Обнять',
    'highfive': 'Дать пять', 
    'scare': 'Испугать',
    'hit': 'Ударить',
    'kiss': 'Поцеловать',
    'slap': 'Шлёпнуть',
    'lick': 'Лизнуть',
    'poison': 'Отравить',
    'congratulate': 'Поздравить',
    'hug_tight': 'Прижать',
    'praise': 'Похвалить',
    'smell': 'Понюхать',
    'pat': 'Погладить',
    'kick': 'Пнуть',
    'feed': 'Покормить',
    'shoot': 'Расстрелять',
    'apologize': 'Извиниться',
    'bite': 'Кусь',
    'castrate': 'Кастрировать',
    'sit': 'Сесть',
    'grope': 'Облапать',
    'encourage': 'Ободрить',
    'choke': 'Задушить',
    'lift': 'Приподнять',
    'play': 'Поиграть',
    'joke': 'Пошутить',
    'clap': 'Похлопать',
    'touch': 'Задеть',
    'thank': 'Поблагодарить',
    'gift': 'Подарить'
}

async def handle_interaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Пожалуйста, ответьте на сообщение пользователя для взаимодействия!")
        return
    
    from_user = update.message.from_user
    to_user = update.message.reply_to_message.from_user
    
    if from_user.id == to_user.id:
        await update.message.reply_text("Вы не можете взаимодействовать с самим собой!")
        return
    
    command = update.message.text[1:].split('@')[0]
    
    interaction_ru = INTERACTION_COMMANDS.get(command)
    if not interaction_ru:
        await update.message.reply_text("Неизвестное взаимодействие")
        return
    
    # Определяем правильное окончание для глагола
    if interaction_ru.endswith('ть'):
        interaction_verb = interaction_ru[:-2] + 'л'
    elif interaction_ru.endswith('ить'):
        interaction_verb = interaction_ru[:-3] + 'ил'
    elif interaction_ru.endswith('еть'):
        interaction_verb = interaction_ru[:-3] + 'ел'
    elif interaction_ru.endswith('ать'):
        interaction_verb = interaction_ru[:-3] + 'ал'
    elif interaction_ru.endswith('ять'):
        interaction_verb = interaction_ru[:-3] + 'ял'
    else:
        interaction_verb = interaction_ru
    
    # Используем универсальную функцию для кликабельных ников
    from_user_mention = create_user_mention(from_user.id, from_user.first_name)
    to_user_mention = create_user_mention(to_user.id, to_user.first_name)
    
    await update.message.reply_text(
        f"{from_user_mention} {interaction_verb.lower()} {to_user_mention}",
        parse_mode='HTML'
    )

# Команды кражи
async def kidnap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Пожалуйста, ответьте на сообщение пользователя, которого хотите похитить!")
        return
    
    kidnapper = update.message.from_user
    victim = update.message.reply_to_message.from_user
    
    if kidnapper.id == victim.id:
        await update.message.reply_text("Вы не можете похитить сами себя!")
        return
    
    # ПРОВЕРКА НА БРАК - ДОБАВЬ ЭТОТ БЛОК
    kidnapper_marriage = get_marriage(kidnapper.id)
    if kidnapper_marriage:
        partner_id = kidnapper_marriage['user2_id'] if kidnapper_marriage['user1_id'] == kidnapper.id else kidnapper_marriage['user1_id']
        if victim.id == partner_id:
            await update.message.reply_text("Вы не можете похитить своего супруга/супругу!")
            return
    
    # Проверяем кулдаун
    can_kidnap_now, remaining_mins = can_kidnap(kidnapper.id)
    if not can_kidnap_now:
        await update.message.reply_text(
            f"У вас закончилось оборудование :(\n"
            f"В следующий раз возможно совершить попытку похищение через {remaining_mins} мин"
        )
        return
    
    # Проверяем, не похитил ли уже кого-то
    existing_kidnap = get_kidnap_info(kidnapper.id)
    if existing_kidnap:
        kidnap_time = datetime.datetime.fromisoformat(existing_kidnap['kidnap_time'])
        end_time = kidnap_time + datetime.timedelta(hours=existing_kidnap['duration_hours'])
        now = datetime.datetime.now()
        
        if now < end_time:
            remaining = end_time - now
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            
            await update.message.reply_text(
                f"Вы уже похитили {existing_kidnap['victim_name']} и будете держать его(её) "
                f"у себя в подвале ещё {hours} ч {minutes} мин"
            )
            return
    
    # Проверяем, состоит ли жертва в браке
    victim_marriage = get_marriage(victim.id)
    if not victim_marriage:
        victim_mention = create_user_mention(victim.id, victim.first_name)
        await update.message.reply_text(f"{victim_mention} не состоит в браке, его невозможно украсть", parse_mode='HTML')
        return
    
    # Обновляем кулдаун
    update_cooldown(kidnapper.id, 'kidnap')
    
    # 10% шанс успеха
    if random.random() <= 0.1:
        conn = sqlite3.connect('marriage_bot.db', check_same_thread=False)
        cursor = conn.cursor()
        
        kidnap_time = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO kidnappings (kidnapper_id, kidnapper_name, victim_id, victim_name, kidnap_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (kidnapper.id, kidnapper.first_name, victim.id, victim.first_name, kidnap_time))
        
        # Обновляем статистику краж
        cursor.execute('''
            INSERT OR REPLACE INTO kidnap_stats (user_id, user_name, kidnap_count)
            VALUES (?, ?, COALESCE((SELECT kidnap_count FROM kidnap_stats WHERE user_id = ?), 0) + 1)
        ''', (kidnapper.id, kidnapper.first_name, kidnapper.id))
        
        conn.commit()
        conn.close()
        
        victim_mention = create_user_mention(victim.id, victim.first_name)
        kidnapper_mention = create_user_mention(kidnapper.id, kidnapper.first_name)
        
        await update.message.reply_text(
            f"{victim_mention} вы были похищены {kidnapper_mention} на 6 часов",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "В этот раз украсть человека не получилось :(\nШанс этого - 10%."
        )

async def escape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    kidnap_info = get_kidnap_victim_info(user.id)
    
    if not kidnap_info:
        await update.message.reply_text("Вас никто не похитил!")
        return
    
    # 10% шанс побега
    if random.random() <= 0.1:
        delete_kidnap(kidnap_info['id'])
        
        # Используем универсальную функцию для кликабельных ников
        kidnapper_mention = create_user_mention(kidnap_info['kidnapper_id'], kidnap_info['kidnapper_name'])
        victim_mention = create_user_mention(kidnap_info['victim_id'], kidnap_info['victim_name'])
        
        await update.message.reply_text(
            f"{kidnapper_mention}, {victim_mention} смог сбежать!",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("Попытка побега не удалась.")

async def kidnap_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    kidnap_info = get_kidnap_info(user.id)
    
    if not kidnap_info:
        user_mention = create_user_mention(user.id, user.first_name)
        await update.message.reply_text(f"{user_mention}, в данный момент у Вас никто не похищен.", parse_mode='HTML')
        return
    
    kidnap_time = datetime.datetime.fromisoformat(kidnap_info['kidnap_time'])
    end_time = kidnap_time + datetime.timedelta(hours=kidnap_info['duration_hours'])
    now = datetime.datetime.now()
    
    if now >= end_time:
        delete_kidnap(kidnap_info['id'])
        user_mention = create_user_mention(user.id, user.first_name)
        await update.message.reply_text(f"{user_mention}, в данный момент у Вас никто не похищен.", parse_mode='HTML')
        return
    
    remaining = end_time - now
    hours = int(remaining.total_seconds() // 3600)
    minutes = int((remaining.total_seconds() % 3600) // 60)
    
    user_mention = create_user_mention(user.id, user.first_name)
    victim_mention = create_user_mention(kidnap_info['victim_id'], kidnap_info['victim_name'])
    
    await update.message.reply_text(
        f"{user_mention}, в данный момент Вы похитили {victim_mention} "
        f"ещё на {hours} ч {minutes} мин",
        parse_mode='HTML'
    )

async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    kidnap_info = get_kidnap_info(user.id)
    
    if not kidnap_info:
        user_mention = create_user_mention(user.id, user.first_name)
        await update.message.reply_text(f"{user_mention}, в данный момент у Вас никто не похищен.", parse_mode='HTML')
    
    delete_kidnap(kidnap_info['id'])
    
    # Используем универсальную функцию для кликабельных ников
    kidnapper_mention = create_user_mention(kidnap_info['kidnapper_id'], kidnap_info['kidnapper_name'])
    victim_mention = create_user_mention(kidnap_info['victim_id'], kidnap_info['victim_name'])
    
    await update.message.reply_text(
        f"{kidnapper_mention} вернул {victim_mention}",
        parse_mode='HTML'
    )

async def kidnappers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_kidnappers = get_top_kidnappers()
    
    if not top_kidnappers:
        await update.message.reply_text("Пока нет статистики похитителей")
        return
    
    text = "🦹 Топ похитителей:\n\n"
    for i, kidnapper in enumerate(top_kidnappers, 1):
        # Получаем ID пользователя из базы данных
        user_id = get_user_id_by_name(kidnapper[0])
        if user_id:
            kidnapper_mention = create_user_mention(user_id, kidnapper[0])
            text += f"{i}. {kidnapper_mention} - {kidnapper[1]} краж\n"
        else:
            text += f"{i}. {kidnapper[0]} - {kidnapper[1]} краж\n"
    
    await update.message.reply_text(text, parse_mode='HTML')

# Команды детей
async def make_love(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    marriage = get_marriage(user.id)
    
    if not marriage:
        await update.message.reply_text("Вы не состоите в браке!")
        return
    
    # Проверяем, не в ссоре ли пара
    argument = get_argument(user.id)
    if argument:
        await update.message.reply_text("Вы в ссоре, невозможно зачать ребенка!")
        return
    
    # Проверяем, не похищен ли кто-то из пары
    kidnap_info1 = get_kidnap_victim_info(user.id)
    partner_id = marriage['user2_id'] if marriage['user1_id'] == user.id else marriage['user1_id']
    kidnap_info2 = get_kidnap_victim_info(partner_id)
    
    if kidnap_info1 or kidnap_info2:
        await update.message.reply_text("Кто-то из пары похищен, невозможно зачать ребенка!")
        return
    
    # 10% шанс зачатия
    if random.random() <= 0.1:
        child_id = create_child(marriage['user1_id'], marriage['user2_id'])
        
        user1_mention = create_user_mention(marriage['user1_id'], marriage['user1_name'])
        user2_mention = create_user_mention(marriage['user2_id'], marriage['user2_name'])
        
        await update.message.reply_text(
            f"🎉 {user1_mention} и {user2_mention} зачали ребёнка! Поздравляю :3\n\n"
            f"А теперь выбери ему имя - /name_{child_id}",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("К сожалению, в этот раз ребёнок не был зачат.")

async def kids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    children = get_children(user.id)
    
    if not children:
        await update.message.reply_text("У вас пока нет детей")
        return
    
    # Получаем информацию о браке для второго родителя
    marriage = get_marriage(user.id)
    if marriage:
        partner_id = marriage['user2_id'] if marriage['user1_id'] == user.id else marriage['user1_id']
        partner_name = marriage['user2_name'] if marriage['user1_id'] == user.id else marriage['user1_name']
        
        user_mention = create_user_mention(user.id, user.first_name)
        partner_mention = create_user_mention(partner_id, partner_name)
        
        text = f"👨‍👩‍👧‍👦 Дети {user_mention} и {partner_mention}:\n\n"
    else:
        user_mention = create_user_mention(user.id, user.first_name)
        text = f"👶 Дети {user_mention}:\n\n"
    
    for i, child in enumerate(children, 1):
        name = child['name'] if child['name'] else "Безымянный"
        text += f"{i}. {name} - {child['age']} лет\n"
    
    await update.message.reply_text(text, parse_mode='HTML')
# В функции name_child замени эту часть:
async def name_child(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    
    # Если команда содержит номер ребенка в формате /name_123
    if update.message.text.startswith('/name_'):
        try:
            child_id = int(update.message.text.split('_')[1])
            # Проверяем, существует ли такой ребенок у пользователя
            children = get_children(user.id)
            child_exists = any(child['id'] == child_id for child in children)
            
            if not child_exists:
                await update.message.reply_text("Ребенок с таким ID не найден или не принадлежит вам")
                return
            
            save_temp_name(user.id, child_id, "")
            await update.message.reply_text("Введите имя которое хотели бы дать ребёнку:")
            return
            
        except (ValueError, IndexError):
            await update.message.reply_text("Неверный формат команды. Используйте: /name_номер_ребенка")
            return
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите номер ребенка: /name номер")
        return

async def handle_child_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    temp_name_info = get_temp_name(user.id)
    
    if not temp_name_info:
        return
    
    name = update.message.text
    update_child_name(temp_name_info['child_id'], name)
    delete_temp_name(user.id)
    
    await update.message.reply_text(f'Вашего ребёнка зовут "{name}"')

async def highchild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите номер ребенка: /highchild номер")
        return
    
    try:
        child_number = int(context.args[0])
        children = get_children(user.id)
        
        if child_number < 1 or child_number > len(children):
            await update.message.reply_text("Ребенок с таким номером не найден")
            return
        
        child = children[child_number - 1]
        increase_child_age(child['id'])
        
        new_age = child['age'] + 1
        name = child['name'] if child['name'] else "Безымянный"
        await update.message.reply_text(
            f"Ваш ребёнок {name} стал старше на 1 год, теперь ему {new_age} лет"
        )
        
    except ValueError:
        await update.message.reply_text("Пожалуйста, укажите корректный номер ребенка")

async def highallchild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    children = get_children(user.id)
    
    if not children:
        await update.message.reply_text("У вас нет детей")
        return
    
    increase_all_children_age(user.id)
    await update.message.reply_text("Все ваши дети успешно стали старше на 1 год")

async def eatchild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите номер ребенка: /eatchild номер")
        return
    
    try:
        child_number = int(context.args[0])
        children = get_children(user.id)
        
        if child_number < 1 or child_number > len(children):
            await update.message.reply_text("Ребенок с таким номером не найден")
            return
        
        child = children[child_number - 1]
        name = child['name'] if child['name'] else "Безымянный"
        await update.message.reply_text(f"Вы успешно покормили своего ребёнка {name}")
        
    except ValueError:
        await update.message.reply_text("Пожалуйста, укажите корректный номер ребенка")

async def eatallchild(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    children = get_children(user.id)
    
    if not children:
        await update.message.reply_text("У вас нет детей")
        return
    
    await update.message.reply_text("Вы успешно покормили всех своих детей")

async def shelter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите номер ребенка: /shelter номер")
        return
    
    try:
        child_number = int(context.args[0])
        children = get_children(user.id)
        
        if child_number < 1 or child_number > len(children):
            await update.message.reply_text("Ребенок с таким номером не найден")
            return
        
        child = children[child_number - 1]
        name = child['name'] if child['name'] else "Безымянный"
        delete_child(child['id'])
        
        await update.message.reply_text(f'Вы сдали своего ребёнка "{name}" в детдом')
        
    except ValueError:
        await update.message.reply_text("Пожалуйста, укажите корректный номер ребенка")

# Разное
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 <b>Доступные команды бота:</b>

💍 <b>Брак:</b>
/propose - Предложить брак (ответом на сообщение)
/marriage_info - Информация о текущем браке
/divorce - Развестись
/marriages - Топ самых долгих браков

😠 <b>Ссоры и примирения:</b>
/argue - Поссориться на день
/make_peace - Помириться

👥 <b>Взаимодействия</b> (используйте ответом на сообщение):
/hug - Обнять
/highfive - Дать пять
/scare - Испугать
/hit - Ударить
/kiss - Поцеловать
/slap - Шлёпнуть
/lick - Лизнуть
/poison - Отравить
/congratulate - Поздравить
/hug_tight - Прижать
/praise - Похвалить
/smell - Понюхать
/pat - Погладить
/kick - Пнуть
/feed - Покормить
/shoot - Расстрелять
/apologize - Извиниться
/bite - Кусь
/castrate - Кастрировать
/sit - Сесть
/grope - Облапать
/encourage - Ободрить
/choke - Задушить
/lift - Приподнять
/play - Поиграть
/joke - Пошутить
/clap - Похлопать
/touch - Задеть
/thank - Поблагодарить
/gift - Подарить

👶 <b>Дети:</b>
/make_love - Попытаться зачать ребенка (10% шанс)
/kids - Список ваших детей
/name - Дать имя ребенку
/highchild - Вырастить ребенка на 1 год
/highallchild - Вырастить всех детей
/eatchild - Покормить ребенка
/eatallchild - Покормить всех детей
/shelter - Сдать ребенка в приют

🦹 <b>Кража:</b>
/kidnap - Попытаться похитить чужую половинку (10% шанс)
/escape - Попытаться сбежать из плена (10% шанс)
/kidnap_info - Информация о текущих похищениях
/release - Освободить похищенного
/kidnappers - Топ похитителей

🎲 <b>Разное:</b>
/info [текст] - Узнать вероятность события
/random [число] - Случайное число
/help - Показать это сообщение

<b>Примечание:</b> Для взаимодействий и предложений брака нужно отвечать на сообщения пользователей!
"""
    await update.message.reply_text(help_text, parse_mode='HTML')

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите текст после команды!")
        return
    
    text = ' '.join(context.args)
    chance = random.randint(0, 100)
    
    await update.message.reply_text(f"вероятность что \"{text}\" - {chance}%")

async def random_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите число/числа после команды!")
        return
    
    try:
        if len(context.args) == 1:
            num1 = int(context.args[0])
            result = random.randint(0, num1)
        else:
            num1 = int(context.args[0])
            num2 = int(context.args[1])
            result = random.randint(num1, num2)
        
        await update.message.reply_text(f"Случайное число: {result}")
    except ValueError:
        await update.message.reply_text("Пожалуйста, укажите целые числа!")

def main():
    # Инициализация базы данных
    init_db()
    
    # Создание приложения
    BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Проверь переменные окружения.")
application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчики команд брака
    application.add_handler(CommandHandler("propose", propose))
    application.add_handler(CommandHandler("marriage_info", marriage_info))
    application.add_handler(CommandHandler("divorce", divorce_cmd))
    application.add_handler(CommandHandler("marriages", marriages))
    
    # Обработчики ссор и примирений
    application.add_handler(CommandHandler("argue", argue))
    application.add_handler(CommandHandler("make_peace", make_peace))
    
    # Обработчики callback'ов
    application.add_handler(CallbackQueryHandler(handle_propose_response, pattern="^propose_"))
    application.add_handler(CallbackQueryHandler(handle_divorce_response, pattern="^divorce_"))
    
    # Обработчики взаимодействий - используем латинские команды
    for command in INTERACTION_COMMANDS.keys():
        application.add_handler(CommandHandler(command, handle_interaction))
    
    # Обработчики кражи
    application.add_handler(CommandHandler("kidnap", kidnap))
    application.add_handler(CommandHandler("escape", escape))
    application.add_handler(CommandHandler("kidnap_info", kidnap_info))
    application.add_handler(CommandHandler("release", release))
    application.add_handler(CommandHandler("kidnappers", kidnappers))
    
    # Обработчики детей
    application.add_handler(CommandHandler("make_love", make_love))
    application.add_handler(CommandHandler("kids", kids))
    application.add_handler(CommandHandler("name", name_child))
    application.add_handler(MessageHandler(filters.Regex(r'^/name_\d+'), name_child))
    application.add_handler(CommandHandler("highchild", highchild))
    application.add_handler(CommandHandler("highallchild", highallchild))
    application.add_handler(CommandHandler("eatchild", eatchild))
    application.add_handler(CommandHandler("eatallchild", eatallchild))
    application.add_handler(CommandHandler("shelter", shelter))
    
    # Обработчик ввода имен детей
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_child_name))
    
    # Обработчики разного (исправленные на латинские команды)
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("random", random_number))
    application.add_handler(CommandHandler("help", help_command))
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
