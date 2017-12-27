import logging
import os
import random

import lxml.html
import requests

from telegram.ext import Updater
from telegram.ext import CommandHandler

import conf
import headers_dump


if conf.debug:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.getLevelName(conf.logging_level)
    )
else:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.getLevelName(conf.logging_level),
        filename='moo.log'
    )
logging.debug('>>> Bot is started!\n')


def get_last_id():
    if os.stat('lastid.flat').st_size == 0:
        return
    with open('lastid.flat', 'r') as _:
        return _.readlines()[0].rstrip()


def save_last_id(last_id):
    with open('lastid.flat', 'w') as _:
        return _.write(last_id)


def find_new_flats(link):
    last_id = get_last_id()
    headers = {'User-Agent': random.choice(headers_dump.HEADERS)}
    response = requests.get(link, headers=headers)
    doc = lxml.html.fromstring(response.content)
    flats = doc.xpath('/html/body/section/article')
    flats_id = [flat.xpath('div/a/@href')[0].split('/')[-1] for flat in flats]
    save_last_id(flats_id[0])
    try:
        index = flats_id.index(last_id)
    except ValueError:
        # Either last_id is None or last_id doesn't present on last page
        # Don't care about last case for a while
        logging.debug('Initialization!')
        return flats_id, True
    if index != 0:
        logging.debug('{} new item(s)'.format(index))
        return flats_id[0:index], False
    logging.debug('There are no new items!')
    return None, False


def run(bot, update, job_queue):
    chat_id = update.message.chat_id
    flats, first_run = find_new_flats(conf.flats_url)

    def notify(flats):
        if flats:
            bot.send_message(chat_id, text='{} new flat(s)'.format(len(flats)))
            for flat in flats:
                bot.send_message(chat_id, text=''.join((conf.full_url, flat)))

    def task(bot, job=None):
        flats, _ = find_new_flats(conf.flats_url)
        notify(flats)

    if first_run:
        bot.send_message(chat_id, text='Started subscription from ==>')
        bot.send_message(chat_id, text=''.join((conf.full_url, flats[0])))
    else:
        notify(flats)
    job_queue.run_repeating(
        task,
        interval=15 * 60,
        context=chat_id
    )


updater = Updater(conf.bot_token)
updater.dispatcher.add_handler(CommandHandler('on', run, pass_job_queue=True))
updater.start_polling()
updater.idle()
