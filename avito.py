import collections
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


Flat = collections.namedtuple('Flat', 'description address price pic link')


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
    flats_list = []
    for flat in flats:
        pic_xpath = """substring-before(substring-after(div/a/div[@class="item-img "]/span/@style, "background-image: url(//"), ")")"""
        pic = flat.xpath(pic_xpath).replace('140x105', '640x480')
        address = flat.xpath('div/a/div[@class="item-info"]/span[@class="info-address info-text"]')[0].text
        price = flat.xpath('div/a/div[@class="item-price"]/span')[0].text
        link = flat.xpath('div/a/@href')[0].split('/')[-1]
        description = flat.xpath('div/a/h3/span')[0].text_content()
        flats_list.append(Flat(description, address, price, pic, link))
    flats_id = [flat.link for flat in flats_list]
    save_last_id(flats_id[0])
    try:
        index = flats_id.index(last_id)
    except ValueError:
        # Either last_id is None or last_id doesn't present on last page
        # Don't care about last case for a while
        logging.debug('Initialization!')
        return flats_list, True
    if index != 0:
        logging.debug('{} new item(s)'.format(index))
        return flats_list[0:index], False
    logging.debug('There are no new items!')
    return None, False


def run(bot, update, job_queue):
    chat_id = update.message.chat_id
    flats, first_run = find_new_flats(conf.flats_url)

    def notify(flats, count=True):
        if flats:
            if count:
                bot.send_message(chat_id, text='{} new flat(s)'.format(len(flats)))
            for flat in flats:
                bot.send_photo(
                    chat_id,
                    flat.pic,
                    caption='{}\n{}\n{}\n{}'.format(
                        flat.description, flat.address, flat.price, ''.join((conf.full_url, flat.link))
                    )
                )

    def task(bot, job=None):
        flats, _ = find_new_flats(conf.flats_url)
        notify(flats)

    if first_run:
        bot.send_message(chat_id, text='Started subscription from ==>')
        notify((flats[0],), count=False)
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
