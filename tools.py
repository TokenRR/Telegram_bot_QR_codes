import telebot


def create_cancel_keyboard():
    """
    Створення клавіатури з кнопкою 'Скасувати'
    """

    markup = telebot.types.InlineKeyboardMarkup()
    itembtn = telebot.types.InlineKeyboardButton('Скасувати', callback_data='cancel')
    markup.add(itembtn)
    return markup