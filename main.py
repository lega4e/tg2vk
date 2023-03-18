#!python3
# Errors:
# - max 50 posts per day

import config
import copy
import lira
import logger
import os
import requests
import telebot
import threading
import time

from mediagroups_checker import MediagroupsChecker
from vk import Vk



vk        = Vk()
tg        = telebot.TeleBot(config.TG_TOKEN)
send      = lambda a, b: tg_send_log_message(a, b)
logStream = logger.LogStream(lira.get_log_subs(), send)
logger.set_stream(logStream)
log       = logger.logger()
mchecker  = MediagroupsChecker(tg, vk, log)



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~                           DECORATORS                           ~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

# Ну надо же что-то вывести, когда бот стартует?
@tg.message_handler(commands=['start'])
def handle_start(m, res=False):
  log.info('/start [%i]' % m.chat.id)
  tg.send_message(m.chat.id, 'Started!')


# Подписаться на логи
@tg.message_handler(commands=['log_subscribe'])
def handle_subscribe(m, res=False):
  log.info('/subscribe [%i]' % m.chat.id)
  lira.put_log_sub(m.chat.id)
  logStream.chats.append(m.chat.id)
  tg.send_message(m.chat.id, 'Success subscribe to log')


# Отписаться от логов
@tg.message_handler(commands=['log_unsubscribe'])
def handle_subscribe(m, res=False):
  log.info('/unsubscribe [%i]' % m.chat.id)
  lira.del_log_sub(m.chat.id)
  if m.chat.id in logStream.chats:
    logStream.chats.remove(m.chat.id)
    tg.send_message(m.chat.id, 'Success unsubscribe to log')


# Текстовые сообщения просто пересылаем без всяких хитростей
@tg.channel_post_handler(content_types=['text'])
def handle_channel_post_text(m):
  log.info('Channel post handler (text): %s' % flatstr(m.text))
  vk.post_text(message=insert_links(m.text, m.json.get('entities')))


# Обработка постов с изображениями: получаем id файла, устанавливаем приписку
@tg.channel_post_handler(content_types=['photo'])
def handle_channel_post_photo(m):
  file_id = list(map(lambda p: p.file_id, m.photo))[-1]
  mchecker.pushMedia(m.media_group_id, file_id)
  if m.caption is not None:
    log.info('Channel post handler (photo): %s' % flatstr(m.caption))
    mchecker.pushCaption(
      m.media_group_id,
      insert_links(m.caption, m.json.get('caption_entities'))
    )



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~                           ACCESSORY                            ~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def flatstr(s):
  return s.replace('\n', '\\n').replace('\t', '\\t')

# Находит ссылки в телегпрамме и добавляет после них пробел и в скобках
# саму ссылку; не очень красиво, но лучшего решения сложно найти
def insert_links(text, entities):
  if entities is None:
    return text

  entities = sorted(entities, key=lambda e: e['offset'])
  pos = 0
  strings = []
  for e in entities:
    if e['type'] == 'text_link':
      s, text = copy_bytes(text, e['offset'] + e['length'] - pos)
      strings.append(s)
      strings.append(' (%s)' % shorten_url(e['url']))
      pos = e['offset'] + e['length']

    elif e['type'] == 'mention':
      s, text = copy_bytes(text, e['offset'] - pos)
      strings.append(s)
      s, text = copy_bytes(text[1:], e['length']-1)
      strings.append('t.me/%s' % s)
      pos = e['offset'] + e['length']

  strings.append(text)
  return ''.join(strings)


def copy_bytes(text, count):
  pos, i, result = 0, 0, []
  while i < len(text):
    if pos >= count:
      break
    result.append(text[i])
    pos += 1 if len(bytes(text[i], encoding='utf-8')) < 4 else 2
    i += 1
  return ''.join(result), text[i:]


def shorten_url(url: str):
  discard_prefixes = ['https://', 'http://']
  for prefix in discard_prefixes:
    if url.startswith(prefix):
      return url[len(prefix):]
  return url



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~                             OTHER                              ~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def tg_send_log_message(chat: int, message: str):
  if len(''.join(filter(lambda s: s not in ' \t\n', message))) != 0:
    while len(message) > 0:
      tg.send_message(chat, message[:config.TG_MESSAGE_MAX_LEN])
      message = message[config.TG_MESSAGE_MAX_LEN:]



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
# ~~~~~                              MAIN                              ~~~~~ #
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

def main():
  log.info('Bot tg2vk started')
  mchecker.start()
  tg.infinity_polling(none_stop=True, interval=0)
  mchecker.kill()
  log.info('Bot tg2vk finished')
  exit(0)



if __name__ == '__main__':
  main()



# END
