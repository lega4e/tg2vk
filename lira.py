import os

from config  import LIRA_LOG_SUBSCRIBERS, LIRA_DATA_FILE, LIRA_HEAD_FILE
from nvxlira import Lira



pwd         = os.path.dirname(__file__)
datafile    = os.path.join(pwd, LIRA_DATA_FILE)
headfile    = os.path.join(pwd, LIRA_HEAD_FILE)
datadirname = os.path.dirname(datafile)
headdirname = os.path.dirname(headfile)

try:    os.mkdir(datadirname)
except: pass

try:    os.mkdir(headdirname)
except: pass

lira = Lira(datafile, headfile)



def get_log_subs() -> [int]:
  return list(map(lambda x: lira.get(x), lira[LIRA_LOG_SUBSCRIBERS]))


def put_log_sub(chat):
  lira.put(chat, cat=LIRA_LOG_SUBSCRIBERS)
  lira.flush()


def del_log_sub(chat) -> [int]:
  lira.out(lira.id(chat))
  lira.flush()



# END
