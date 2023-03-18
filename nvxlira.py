# 
# author:   lis
# created: 2021.03.01 01:04:18
# 
import pickle

from threading import Lock



class Lira:
	'''
	Lira — это класс, предназначенный для выборочной
	синхронизации объектов в оперативной памяти и на
	жёстком диске. Потокобезопасна, т.е. можно
	пользоваться из разных потоков одновременно, не
	прибегая к блокировкам и мьютексам

	Важно! Лира не записывает заголовки автоматически,
	это нужно делать вручную с помощью метода flush.

	Тоже важно! Если в Лиру был записан объект, а затем
	изменён, то в памяти останется тот, что был записан;
	Лира не отслеживает изменения объектов; поэтому,
	чтобы обновить объект, необходимо его перезаписать:
	lira.put(obj, id=lira.id(obj), cat=lira.cat(obj))


	Примеры использования Лиры:

	lira = Lira('data.bin', 'head.bin') # Создание Лиры
	lira.apple = 'Value of id apple'    # Добавление нового объекта

	# Получение объекта по id
	print(lira.apple)
	print(lira.get('apple'))

	lira.put('value', id=1) # Добавление с помощью put

	for i in range(10): # Добавление с категорией
		lira.put(random.randint(0, 100), cat='randint')

	for id in lira['cat']: # Получение всех объектов категории
		print(lira.get(id))

	# Получение всех категорий
	for cat in lira.cats():
		print(cat)

	# Получение всех id
	for id in lira:
		print(id)
	'''

	def __init__(self, _data, _head):
		'''
		При создании необходимо указать два аргумента:
		_data — имя файла для хранения самих объектов
		_head — и имя файла заголовков
		'''
		self.__dict__['_fpls'] = { (0, 2**40) }
		self.__dict__['_objs'] = dict()
		self.__dict__['_objv'] = dict()
		self.__dict__['_cats'] = dict()
		self.__dict__['_mnid'] = -1
		self.__dict__['_lock'] = Lock()
		self.__dict__['_chng'] = False
		try:
			self.__dict__['_data'] = open(_data, 'rb+')
		except:
			self.__dict__['_data'] = open(_data, 'wb+')
		self.__dict__['_head'] = _head
		self.read_head()
		return



	def flush(self):
		'''
		Если с предыдущего раза Лира изменилась, то
		все объекты, которые были записаны в файл данных
		извлекаются из буффера и переносятся непосредственно
		в файл, а также перезаписывается файл заголовков
		'''
		if not self._chng:
			return
		self._data.flush()
		self.write_head()
		self.__dict__['_chng'] = False
		return

	def changed(self):
		'Проверяет, была ли Лира изменена'
		return self.__dict__['_chng']



	def read_head(self, _head=None):
		'Читает файл заголовков'
		with self._lock:
			if _head is None:
				_head = self._head;
			try:
				with open(_head, 'rb') as file: # if can't open ?
					self.__dict__['_fpls'] = pickle.load(file)
					self.__dict__['_objs'] = pickle.load(file)
					self.__dict__['_cats'] = pickle.load(file)
				self.__dict__['_mnid'] = min(
					filter(lambda x: isinstance(x, int), self._objs.keys())
				) - 1
			except:
				pass
		return

	def write_head(self, head=None):
		'Пишет файл заголовков'
		with self._lock:
			if head is None:
				head = self._head;
			with open(head, 'wb') as file:
				pickle.dump(self._fpls, file)
				pickle.dump(self._objs, file)
				pickle.dump(self._cats, file)
		return

	def cat(self, id):
		'''
		Возвращает категорию объекта с заданным id;
		если такового нет, возбуждается KeyError
		'''
		with self._lock:
			return self._objs[id][1]

	def id(self, obj):
		'''
		Возвращает id первого найденного в словаре
		равного объекта объекту obj; осторожно! —
		если есть дублирующиеся объекты, будет выбран
		первый попавшийся; проверка идёт только среди
		тех объектов, которые находятся в памети, т.е.
		либо этот объект был записан в данной сессии,
		либо получен. Если объект не найден, возвращается
		None
		'''
		for id, val in self._objv.items():
			if val == obj:
				return id
		return None



	def cats(self):
		'Итератор по всем категориям'
		return self._cats.keys()

	def __iter__(self):
		'Итератор по всем id'
		for key in self._objs.keys():
			yield key


	def get(self, id, default=None):
		'''
		Получение объекта по id; если такового
		нет, возвращается default (по умолчанию
		None)
		'''
		with self._lock:
			obj = self._objv.get(id, None)
			if obj is not None:
				return obj

			pl = self._objs.get(id, None)
			if pl is None:
				return default
			pl = pl[0]

			self._data.seek(pl[0], 0)
			dump = self._data.read(pl[1])
			obj = pickle.loads(dump)

			self._objv[id] = obj;
		return obj

	def put(self, obj, *, id=None, cat=None, meta=None):
		'''
		Записывает новый объект obj в Лиру; возвращает
		id объекта. Если указан существующий id, то
		прежний объект будет удалён и замещён новым;
		дополнительно можно указать категорию объекта,
		а также метаинформацию, которая будет помещена
		в файл заголовков
		'''
		if id is not None:
			self.out(id)
		with self._lock:
			if id is None:
				id = self._nextid()
			id = self._put(obj, id, cat, meta)
		return id



	def out(self, id):
		'''
		Удаление существующего объекта; ничего
		не возвращает
		'''
		self.__dict__['_chng'] = True
		with self._lock:
			obj = self._objs.pop(id, None)
			if obj is None:
				return None;
			self._objv.pop(id, None)

			self._free(obj[0])
			self._cats[obj[1]].remove(id)
		return

	def pop(self, id, default=None):
		'Удаляет объект и возвращает его'
		val = self.get(id, default)
		self.out(id)
		return val



	def __call__(self, id, default=None):
		'''
		Вызов Лиры как функции — то же самое,
		что получение объекта по id
		'''
		return self.get(id, default)

	def __getattr__(self, attr):
		'Атрибут воспринимается как id'
		return self.get(attr)

	def __setattr__(self, attr, value):
		'Атрибут воспринимается как id'
		return self.put(value, id=attr)

	def __delattr__(self, attr):
		'Атрибут воспринимается как id'
		return self.out(attr)

	def __getitem__(self, item):
		'''
		Через индексацию можно получить список
		всех id элементов данной категории
		'''
		with self._lock:
			return list(self._cats.get(item, []))



	def _put(self, obj, id, cat, meta):
		self.__dict__['_chng'] = True
		dump = pickle.dumps(obj)
		pl = self._malloc(len(dump))

		self._data.seek(pl[0], 0)
		self._data.write(dump)

		self._objs[id] = (pl, cat, meta);
		self._objv[id] = obj
		self._cats.setdefault(cat, set()).add(id)
		return id



	def _free(self, pl):
		self._fpls.add(pl)

		l = r = None
		for fpl in self._fpls:
			if fpl[0] + fpl[1] == pl[0]:
				l = fpl
			elif pl[0] + pl[1] == fpl[0]:
				r = fpl

		if l is not None:
			self._fpls.remove(l)
			self._fpls.remove(pl)
			pl = (l[0], l[1] + pl[1])
			self._fpls.add(pl)

		if r is not None:
			self._fpls.remove(r)
			self._fpls.remove(pl)
			pl = (pl[0], pl[1] + r[1])
			self._fpls.add(pl)

		return

	def _malloc(self, s):
		best = None
		for el in self._fpls:
			if el[1] >= s and (best is None or el[1] < best[1]):
				best = el

		if best is None:
			raise Exception("memory out")

		self._fpls.remove(best)
		if s != best[1]:
			self._fpls.add( (best[0] + s, best[1] - s) )

		return (best[0], s)

	def _nextid(self):
		self.__dict__['_mnid'] = self._mnid - 1;
		return self._mnid + 1





# END
