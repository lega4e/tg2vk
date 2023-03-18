import config
import os
import threading
import time
import traceback



class MediaGroup:
  def __init__(self, group, files = [], caption = None):
    self.group = group
    self.files = files
    self.caption = caption



class MediagroupsChecker(threading.Thread):
  def __init__(self, tg, vk, log=None):
    super().__init__()
    self.tg                  = tg
    self.vk                  = vk
    self.log                 = log if log is not None else config.logger()
    self.update_counter      = config.TG_UPDATE_COUNT
    self.update_counter_lock = threading.Lock()
    self.runflag             = True
    self.runflag_lock        = threading.Lock()
    self.mediagroups         = []
    self.mediagroups_lock    = threading.Lock()


  def isRun(self):
    with self.runflag_lock:
      return self.runflag


  def kill(self):
    with self.runflag_lock:
      self.runflag = False


  def pushMedia(self, group: int, file_id: str):
    with self.mediagroups_lock:
      mg = self._findGroup(group)
      if mg is not None:
        mg.files.append(file_id)
      else:
        self.mediagroups.append(MediaGroup(group, [file_id]))


  def pushCaption(self, group: int, caption: str):
    with self.mediagroups_lock:
      mg = self._findGroup(group)
      if mg is None:
        raise Exception('Unknown media group in MediagroupsChecker.pushCaption')
      mg.caption = caption


  def run(self):
    self.log.info('MediagroupsChecker.run started')
    while self.isRun():
      time.sleep(config.TG_UPDATE_DELAY / 1000)
      if self._decreaseUpdateCounter() > 0:
        continue

      with self.mediagroups_lock:
        mgs = self.mediagroups
        self.mediagroups = []
      self._resetUpdateCounter()

      for mg in mgs:
        try:
          self._post_mediagroup(mg)
        except Exception as e: 
          self.log.error(traceback.format_exc())

    self.log.info('MediagroupsChecker.run finished')


  def _findGroup(self, group) -> MediaGroup:
    for mg in self.mediagroups:
      if group == mg.group:
        return mg
    return None


  def _resetUpdateCounter(self):
    with self.update_counter_lock:
      self.update_counter = config.TG_UPDATE_COUNT


  def _decreaseUpdateCounter(self):
    with self.update_counter_lock:
      self.update_counter -= 1
      return self.update_counter


  # Загружает файлы из тг по айдишникам и выкладывает одним постом с припиской
  def _post_mediagroup(self, mg: MediaGroup):
    file_names = list(map(self._save_file, mg.files))

    self.log.info('Post photos: %s' % str(file_names))
    self.vk.post_photo(
      message = mg.caption,
      photos  = file_names,
    )

    for file_name in file_names:
      os.remove(file_name)


  # Загружает и сохраняет на диск файл по его идентификатору в телеграмме
  def _save_file(self, file_id: str) -> str:
    self.log.info('Save file %s' % file_id)
    file_info = self.tg.get_file(file_id=file_id)
    file_data = self.tg.download_file(file_info.file_path)
    file_name = os.path.basename(file_info.file_path)
    with open(file_name, 'wb') as file:
      file.write(file_data)
    return file_name



# END
