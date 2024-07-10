import re
from io import BytesIO
from functools import partial

import qrcode
import telebot
from PIL import Image
from pyzbar.pyzbar import decode

from config import TOKEN
from tools import create_cancel_keyboard


# Ініціалізація бота
bot = telebot.TeleBot(TOKEN)
bot.set_my_commands([
    telebot.types.BotCommand('/start', 'Привітання'),
    telebot.types.BotCommand('/help', 'Інструкція по використанню бота'),
    telebot.types.BotCommand('/create_qr_for_parcel', 'Створення QR-коду для посилки'),
    telebot.types.BotCommand('/create_qr', 'Створення QR-коду за Вашими даними'),
    telebot.types.BotCommand('/scan_qr', 'Сканування QR-коду'),
])

# Збереження стану користувача
user_data = {}

# Регулярні вирази для перевірки ПІБ і номеру телефону
pib_pattern = re.compile(r'^[А-ЯІЇЄҐа-яіїєґ\']+ [А-ЯІЇЄҐа-яіїєґ\']+ [А-ЯІЇЄҐа-яіїєґ\']+$')
phone_pattern = re.compile(r'^\+38 \(\d{3}\) \d{3}-\d{2}-\d{2}$')




def handle_qr_creation(bot, message):
    if 'msgs' not in user_data.get(message.chat.id, {}):
        return

    user_data[message.chat.id]['message'] = message.text
    for msg_id in user_data[message.chat.id]['msgs']:
        bot.delete_message(message.chat.id, msg_id)
    bot.delete_message(message.chat.id, message.message_id)

    # Генерація QR-коду
    qr_data = user_data[message.chat.id]['message']
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # Збереження зображення у BytesIO об'єкт
    img_byte_arr = BytesIO()
    img.save(img_byte_arr)
    img_byte_arr.seek(0)

    # Відправка зображення QR-коду користувачу
    bot.send_photo(message.chat.id, img_byte_arr, caption=f'Створений QR-код за вашими даними: \n\n{qr_data}')

    user_data.pop(message.chat.id, None)




@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, 'Вітаю! Цей бот - це частина дипломної роботи Лунгова Олександра Віталійовича про логістичні перевезення \nВикористайте команду /help для виведення списку доступних команд')


@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, '/start - привітання \n/help - інструкція по використанню бота \n/create_qr_for_parcel - створення QR-коду для посилки \n/create_qr - створення QR-коду за Вашими даними \n/scan_qr - сканування QR-коду')


@bot.message_handler(commands=['create_qr_for_parcel'])
def send_welcome(message):
    user_data[message.chat.id] = {'msgs': []}
    msg = bot.send_message(message.chat.id, 'Введіть ПІБ відправника, наприклад: \nПетренко Петро Петрович', reply_markup=create_cancel_keyboard())
    user_data[message.chat.id]['msgs'].append(msg.message_id)


@bot.message_handler(commands=['create_qr'])
def send_welcome(message):
    user_data[message.chat.id] = {'msgs': []}
    msg = bot.send_message(message.chat.id, 'Введіть повідомлення, яке треба закодувати', reply_markup=create_cancel_keyboard())
    user_data[message.chat.id]['msgs'].append(msg.message_id)
    bot.register_next_step_handler(msg, partial(handle_qr_creation, bot))


@bot.message_handler(commands=['scan_qr'])
def scan_qr_command(message):
    bot.send_message(message.chat.id, 'Надішліть QR-код (фото або файл)')




@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def cancel_callback(call):
    bot.answer_callback_query(call.id, 'Дію скасовано')
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    if call.message.chat.id in user_data:
        user_data.pop(call.message.chat.id, None)


@bot.callback_query_handler(func=lambda call: call.data == "send_contact")
def request_contact(call):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(telebot.types.KeyboardButton('Надіслати контакт', request_contact=True))
    msg = bot.send_message(call.message.chat.id, 'Натисніть кнопку, щоб надіслати свій контакт:', reply_markup=markup)
    user_data[call.message.chat.id]['msgs'].append(msg.message_id)




@bot.message_handler(content_types=['contact'])
def get_contact(message):
    if 'msgs' not in user_data.get(message.chat.id, {}):
        return
    
    msg = bot.send_message(message.chat.id, "Ваш контакт отримано!", reply_markup=telebot.types.ReplyKeyboardRemove())
    user_data[message.chat.id]['msgs'].append(msg.message_id)
    
    for msg_id in user_data[message.chat.id]['msgs']:
            bot.delete_message(message.chat.id, msg_id)
    bot.delete_message(message.chat.id, message.message_id)
    
    phone = message.contact.phone_number
    phone = "+" + phone if not phone.startswith("+") else phone
    formatted_phone = f'+38 ({phone[3:6]}) {phone[6:9]}-{phone[9:11]}-{phone[11:13]}'

    if phone_pattern.match(formatted_phone):
        if 'pib' in user_data[message.chat.id] and 'phone' not in user_data[message.chat.id] \
            and 'pib_receiver' not in user_data[message.chat.id] and 'phone_receiver' not in user_data[message.chat.id]:
            msg_help = user_data[message.chat.id]['pib']
            msg = bot.send_message(message.chat.id, f'Ваші дані: \n\nПІБ відправника: {msg_help} \nТелефон відправника: {formatted_phone}')
            user_data[message.chat.id]['msgs'] = [msg.message_id]
            user_data[message.chat.id]['phone'] = formatted_phone

            msg = bot.send_message(message.chat.id, 'Введіть ПІБ отримувача', reply_markup=create_cancel_keyboard())
            user_data[message.chat.id]['msgs'].append(msg.message_id)

        if 'pib' in user_data[message.chat.id] and 'phone' in user_data[message.chat.id] \
            and 'pib_receiver' in user_data[message.chat.id] and 'phone_receiver' not in user_data[message.chat.id]:
            pib_help = user_data[message.chat.id]['pib']
            phone_help = user_data[message.chat.id]['phone']
            pib_receiver_help = user_data[message.chat.id]['pib_receiver']

            msg = bot.send_message(message.chat.id, f'Ваші дані: \n\nПІБ відправника: {pib_help} \nТелефон відправника: {phone_help} \nПІБ отримувача: {pib_receiver_help} \nТелефон отримувача: {formatted_phone} ')
            user_data[message.chat.id]['msgs'] = [msg.message_id]
            user_data[message.chat.id]['phone_receiver'] = formatted_phone

            msg = bot.send_message(message.chat.id, 'Введіть адресу доставки', reply_markup=create_cancel_keyboard())
            user_data[message.chat.id]['msgs'].append(msg.message_id)
    else:
        msg = bot.send_message(message.chat.id, f'Ваші дані: \n\nПІБ: {message.text}')
        user_data[message.chat.id]['msgs'].append(msg.message_id)
        msg = bot.send_message(message.chat.id, 'Некоректний формат номеру телефону. Будь ласка, введіть номер у форматі +38 (000) 000-00-00', reply_markup=create_cancel_keyboard())
        user_data[message.chat.id]['msgs'].append(msg.message_id)


@bot.message_handler(content_types=['photo', 'document'])
def handle_qr_code(message):
    try:
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
        elif message.content_type == 'document' and message.document.mime_type.startswith('image/'):
            file_info = bot.get_file(message.document.file_id)
        else:
            bot.send_message(message.chat.id, "Неправильний формат файлу. Надішліть зображення QR-коду")
            return

        downloaded_file = bot.download_file(file_info.file_path)

        # Відкриття зображення
        img = Image.open(BytesIO(downloaded_file))

        # Декодування QR-коду
        decoded_objects = decode(img)
        if decoded_objects:
            for obj in decoded_objects:
                data = obj.data.decode('utf-8')
                # Перевірка типу даних
                if re.match(r'^https?://', data):
                    bot.reply_to(message, f"Це посилання: {data}")
                else:
                    bot.reply_to(message, f"{data}")
        else:
            bot.send_message(message.chat.id, "Не вдалося зчитати QR-код. Спробуйте ще раз")
    except Exception as e:
        bot.send_message(message.chat.id, f"Виникла помилка при зчитуванні QR-коду")

    


@bot.message_handler(func=lambda message: message.chat.id in user_data 
                     and 'pib' not in user_data[message.chat.id])
def get_pib(message):
    if 'msgs' not in user_data.get(message.chat.id, {}):
        return

    if pib_pattern.match(message.text):
        for msg_id in user_data[message.chat.id]['msgs']:
            bot.delete_message(message.chat.id, msg_id)
        bot.delete_message(message.chat.id, message.message_id)

        msg = bot.send_message(message.chat.id, f'Ваші дані: \n\nПІБ відправника: {message.text}')
        user_data[message.chat.id]['msgs'] = [msg.message_id]
        user_data[message.chat.id]['pib'] = message.text

        markup = telebot.types.InlineKeyboardMarkup()
        button_send_contact = telebot.types.InlineKeyboardButton("Надіслати контакт", callback_data="send_contact")
        button_cancel = telebot.types.InlineKeyboardButton("Скасувати", callback_data="cancel")
        markup.row(button_send_contact, button_cancel)
        msg = bot.send_message(message.chat.id, 'Тепер введіть номер телефону відправника у форматі +38 (000) 000-00-00 або надішліть свій контакт через Telegram',reply_markup=markup)
        user_data[message.chat.id]['msgs'].append(msg.message_id)
    else:
        msg = bot.send_message(message.chat.id, 'Некоректний формат ПІБ. Будь ласка, спробуйте ще раз', reply_markup=create_cancel_keyboard())
        user_data[message.chat.id]['msgs'].append(msg.message_id)
        user_data[message.chat.id]['msgs'].append(msg.message_id-1)


@bot.message_handler(func=lambda message: message.chat.id in user_data 
                     and 'phone' not in user_data[message.chat.id])
def get_phone(message):
    if 'msgs' not in user_data.get(message.chat.id, {}):
        return

    if phone_pattern.match(message.text):
        for msg_id in user_data[message.chat.id]['msgs']:
            bot.delete_message(message.chat.id, msg_id)
        bot.delete_message(message.chat.id, message.message_id)

        msg_help = user_data[message.chat.id]['pib']
        msg = bot.send_message(message.chat.id, f'Ваші дані: \n\nПІБ відправника: {msg_help} \nТелефон відправника: {message.text}')
        user_data[message.chat.id]['msgs'] = [msg.message_id]

        user_data[message.chat.id]['phone'] = message.text

        msg = bot.send_message(message.chat.id, 'Введіть ПІБ отримувача', reply_markup=create_cancel_keyboard())
        user_data[message.chat.id]['msgs'].append(msg.message_id)
    else:
        msg = bot.send_message(message.chat.id, 'Некоректний формат номеру телефону. Будь ласка, введіть номер у форматі +38 (000) 000-00-00', reply_markup=create_cancel_keyboard())
        user_data[message.chat.id]['msgs'].append(msg.message_id)


@bot.message_handler(func=lambda message: message.chat.id in user_data 
                     and 'pib_receiver' not in user_data[message.chat.id]
                     and 'pib' in user_data[message.chat.id])
def get_pib(message):
    if 'msgs' not in user_data.get(message.chat.id, {}):
        return

    if pib_pattern.match(message.text):
        for msg_id in user_data[message.chat.id]['msgs']:
            bot.delete_message(message.chat.id, msg_id)
        bot.delete_message(message.chat.id, message.message_id)

        msg_pib = user_data[message.chat.id]['pib']
        msg_phone = user_data[message.chat.id]['phone']
        msg = bot.send_message(message.chat.id, f'Ваші дані: \n\nПІБ відправника: {msg_pib} \nТелефон відправника: {msg_phone} \nПІБ отримувача: {message.text}')
        user_data[message.chat.id]['msgs'] = [msg.message_id]
        user_data[message.chat.id]['pib_receiver'] = message.text

        markup = telebot.types.InlineKeyboardMarkup()
        button_send_contact = telebot.types.InlineKeyboardButton("Надіслати контакт", callback_data="send_contact")
        button_cancel = telebot.types.InlineKeyboardButton("Скасувати", callback_data="cancel")
        markup.row(button_send_contact, button_cancel)
        msg = bot.send_message(message.chat.id, 'Тепер введіть номер телефону отримувача у форматі +38 (000) 000-00-00 або надішліть свій контакт через Telegram',reply_markup=markup)
        user_data[message.chat.id]['msgs'].append(msg.message_id)
    else:
        msg = bot.send_message(message.chat.id, 'Некоректний формат ПІБ. Будь ласка, спробуйте ще раз', reply_markup=create_cancel_keyboard())
        user_data[message.chat.id]['msgs'].append(msg.message_id)
        user_data[message.chat.id]['msgs'].append(msg.message_id-1)


@bot.message_handler(func=lambda message: message.chat.id in user_data 
                     and 'phone_receiver' not in user_data[message.chat.id]
                     and 'phone' in user_data[message.chat.id])
def get_phone(message):
    if 'msgs' not in user_data.get(message.chat.id, {}):
        return

    if phone_pattern.match(message.text):
        for msg_id in user_data[message.chat.id]['msgs']:
            bot.delete_message(message.chat.id, msg_id)
        bot.delete_message(message.chat.id, message.message_id)

        pib_help = user_data[message.chat.id]['pib']
        phone_help = user_data[message.chat.id]['phone']
        pib_receiver_help = user_data[message.chat.id]['pib_receiver']
        msg = bot.send_message(message.chat.id, f'Ваші дані: \n\nПІБ відправника: {pib_help} \nТелефон відправника: {phone_help} \nПІБ отримувача: {pib_receiver_help} \nТелефон отримувача: {message.text} ')
        user_data[message.chat.id]['msgs'] = [msg.message_id]

        user_data[message.chat.id]['phone_receiver'] = message.text

        msg = bot.send_message(message.chat.id, 'Введіть адресу доставки', reply_markup=create_cancel_keyboard())
        user_data[message.chat.id]['msgs'].append(msg.message_id)
    else:
        msg = bot.send_message(message.chat.id, 'Некоректний формат номеру телефону. Будь ласка, введіть номер у форматі +38 (000) 000-00-00', reply_markup=create_cancel_keyboard())
        user_data[message.chat.id]['msgs'].append(msg.message_id)


@bot.message_handler(func=lambda message: message.chat.id in user_data 
                     and 'pib' in user_data[message.chat.id] 
                     and 'phone' in user_data[message.chat.id]
                     and 'pib_receiver' in user_data[message.chat.id]
                     and 'phone_receiver' in user_data[message.chat.id]
                     and 'adress' not in user_data[message.chat.id])
def get_adress(message):
    if 'msgs' not in user_data.get(message.chat.id, {}):
        return

    for msg_id in user_data[message.chat.id]['msgs']:
        bot.delete_message(message.chat.id, msg_id)
    bot.delete_message(message.chat.id, message.message_id)

    pib_help = user_data[message.chat.id]['pib']
    phone_help = user_data[message.chat.id]['phone']
    pib_receiver_help = user_data[message.chat.id]['pib_receiver']
    phone_receiver_help = user_data[message.chat.id]['phone_receiver']

    msg = bot.send_message(message.chat.id, f'Ваші дані: \n\nПІБ відправника: {pib_help} \nТелефон відправника: {phone_help} \nПІБ отримувача: {pib_receiver_help} \nТелефон отримувача: {phone_receiver_help} \nАдреса доставки: {message.text}')
    
    user_data[message.chat.id]['msgs'] = [msg.message_id]
    user_data[message.chat.id]['adress'] = message.text

    msg = bot.send_message(message.chat.id, 'Введіть додаткову інформацію про посилку', reply_markup=create_cancel_keyboard())
    user_data[message.chat.id]['msgs'].append(msg.message_id)


@bot.message_handler(func=lambda message: message.chat.id in user_data 
                     and 'pib' in user_data[message.chat.id] 
                     and 'phone' in user_data[message.chat.id]
                     and 'pib_receiver' in user_data[message.chat.id]
                     and 'phone_receiver' in user_data[message.chat.id]
                     and 'adress' in user_data[message.chat.id])
def get_message_for_qr(message):
    if 'msgs' not in user_data.get(message.chat.id, {}):
        return

    user_data[message.chat.id]['message'] = message.text

    for msg_id in user_data[message.chat.id]['msgs']:
            bot.delete_message(message.chat.id, msg_id)
    bot.delete_message(message.chat.id, message.message_id)

    # Формування даних для QR-коду
    pib_help = user_data[message.chat.id]['pib']
    phone_help = user_data[message.chat.id]['phone']
    pib_receiver_help = user_data[message.chat.id]['pib_receiver']
    phone_receiver_help = user_data[message.chat.id]['phone_receiver']
    adress_help = user_data[message.chat.id]['adress']
    message_help = user_data[message.chat.id]['message']
    qr_data = f"ПІБ відправника: {pib_help} \nТелефон відправника: {phone_help} \n\nПІБ отримувача: {pib_receiver_help} \nТелефон отримувача: {phone_receiver_help} \n\nАдреса доставки: {adress_help} \nДодаткова інформація: {message_help}"

    # Генерація QR-коду
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    # Збереження зображення у BytesIO об'єкт
    img_byte_arr = BytesIO()
    img.save(img_byte_arr)
    img_byte_arr.seek(0)

    # Відправка зображення QR-коду користувачу
    bot.send_photo(message.chat.id, img_byte_arr, caption=f'Створений QR-код за вашими даними: \n\n{qr_data}')

    user_data.pop(message.chat.id, None)


bot.polling()
