import logging

from sys import stdout
from config import LOGGING_DATE_FORMAT, LOGGING_FORMAT



_logger = None
_stream = None



class LogSubscription:
  def __init__(self, chatid):
    self.chatid = chatid


class LogStream:
  def __init__(self, chats: [int], send_message):
    self.chats        = chats
    self.send_message = send_message

  def write(self, record):
    try:
      stdout.write(record)
    except:
      stdout.write('ERROR WITH LOG')
      record = '(E) ' + record
    for chat in self.chats:
      self.send_message(chat, record)


def set_stream(stream: LogStream):
  global _stream
  if _stream is not None:
    raise Exception('Double initialization of stream (logger)')
  _stream = stream


def logger() -> logging.Logger:
  global _logger
  if _stream is None:
    raise Exception('Before get logger need to set stream')
  if _logger is None:
    logging.basicConfig(
      format=LOGGING_FORMAT,
      datefmt=LOGGING_DATE_FORMAT,
      stream=_stream,
    )
    _logger = logging.getLogger(__name__)
    _logger.setLevel(logging.INFO)
  return _logger



# END
