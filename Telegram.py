import random
import telebot
from telebot import types
import sqlite3

bot = telebot.TeleBot("6697328507:AAFMTwmhcGDEVHd3WGPr8MsG73W6CxLsr4U")

conn = sqlite3.connect('db/database.db', check_same_thread=False)
cursor = conn.cursor()


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    but1 = types.KeyboardButton("Advert")
    but2 = types.KeyboardButton("Design")
    markup.add(but1, but2)
    bot.send_message(message.chat.id, "Выбери юнит:", reply_markup=markup, parse_mode='html')


@bot.message_handler(func=lambda message: message.text in ['Advert', 'Design'])
def choose_topic(message):
    cursor = conn.cursor()
    user_id = message.from_user.id
    topic_name = message.text
    topic_id = switch_case(topic_name)

    cursor.execute("""SELECT COUNT(*) FROM UserWords WHERE user_id = ?;""", (user_id,))
    user_topic_exists = cursor.fetchone()[0]
    cursor.close()
    cursor = conn.cursor()

    cursor.execute("""SELECT COUNT(*) FROM Users WHERE user_id = ?;""", (user_id,))
    user_topic_exists1 = cursor.fetchone()[0]

    if not user_topic_exists:
        cursor.execute("""
                INSERT INTO UserWords (user_id, word_id, usage_weight)
                SELECT ?, word_id, weight FROM Words WHERE topic_id = ?;
            """, (user_id, topic_id))
        conn.commit()
    if not user_topic_exists1:
        cursor.execute("INSERT INTO Users (user_id, last_topic) VALUES (?, ?)", (user_id, topic_id,))
        conn.commit()

    get_random_word(user_id, topic_id, message)


def switch_case(argument):
    switch_dict = {
        'Advert': 1,
        'Design': 2,
    }

    return switch_dict.get(argument, "Invalid case")


def get_random_word(user_id, topic_id, message):

    cursor.execute("""
                    SELECT last_word
                    FROM Users
                    WHERE user_id = ?;
                """, (message.from_user.id,))
    last_word = cursor.fetchone()[0]

    cursor.execute("""
        SELECT Words.word, UserWords.usage_weight 
        FROM Words
        JOIN UserWords ON Words.word_id = UserWords.word_id
        WHERE Words.topic_id = ? AND UserWords.user_id = ? AND Words.word != ?;
    """, (topic_id, user_id, last_word,))

    words_with_weights = cursor.fetchall()

    if words_with_weights:
        words, usage_weights = zip(*words_with_weights)
        selected_word = random.choices(words, usage_weights)[0]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        but1 = types.KeyboardButton("Знаю")
        but2 = types.KeyboardButton("Не знаю")
        markup.add(but1, but2)
        bot.send_message(message.from_user.id, selected_word, reply_markup=markup, parse_mode='html')
        cursor.execute("UPDATE Users SET last_word = ? WHERE user_id = ? AND last_topic = ?",
                       (selected_word, user_id, topic_id))
    else:
        return None


@bot.message_handler(func=lambda message: message.text in ['Знаю', 'Не знаю'])
def on_user_response(message):
    cursor = conn.cursor()
    cursor.execute("""
                SELECT last_word, last_topic
                FROM Users
                WHERE user_id = ?;
            """, (message.from_user.id,))
    last_info = cursor.fetchone()

    user_id = message.from_user.id

    cursor.execute("""
        SELECT word_id, translation, weight
        FROM Words
        WHERE word = ?;
    """, (last_info[0],))
    word_info = cursor.fetchone()

    if word_info is not None:
        cursor.execute("""
                            SELECT usage_weight
                            FROM UserWords
                            WHERE word_id = ? AND user_id = ?;
                        """, (word_info[0], user_id))
        w = cursor.fetchone()

        if message.text == 'Знаю':
            if word_info and w:
                word, translation, weight = word_info
                bot.send_message(message.from_user.id,f"Напоминаю🤓:\n{translation}", parse_mode = 'html')
                usage_weight = w[0]
                usage_weight /= 1.5
                cursor = conn.cursor()
                cursor.execute("UPDATE UserWords SET usage_weight = ? WHERE user_id = ? AND word_id = ?",
                               (usage_weight, user_id, word_info[0]))
                conn.commit()
                cursor.close()
                get_random_word(user_id, last_info[1], message)
            else:
                bot.send_message(message.from_user.id,f"Произошла ошибка😢, обратитесь к @lrawd3", parse_mode = 'html')
        if message.text == 'Не знаю':
            if word_info:
                word, translation, weight = word_info
                bot.send_message(message.from_user.id, f"Перевод😉:\n{translation}", parse_mode='html')
                get_random_word(user_id, last_info[1], message)
            else:
                bot.send_message(message.from_user.id, f"Произошла ошибка😢, обратитесь к @lrawd3", parse_mode='html')
    else:
        bot.send_message(message.from_user.id, f"Я твой рот ебал\nВозникла ошибка\nПропиши /start", parse_mode='html')


bot.polling(none_stop=True)
