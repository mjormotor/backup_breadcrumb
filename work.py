"""
/* --------------------------------
   Models of application business

 - processes about program output
-------------------------------- */
"""
import datetime
import logging
import os
import re
import shutil

from PySide6.QtCore import QObject, Signal
from watchdog.events import FileCreatedEvent, FileDeletedEvent, FileModifiedEvent, FileMovedEvent, FileSystemEventHandler
from watchdog.observers import Observer

import path


class File(QObject):
	"""
	file version controller
	"""
	class Version:
		def __init__(self, key, file_path):
			self.__key = key
			self.__repository_file_path = file_path
			self.__setup()
		
		@property
		def key(self):
			return self.__key
		
		@property
		def is_reversion(self):
			return self.__is_reversion
		
		@property
		def repository_file_path(self):
			return self.__repository_file_path
		
		@property
		def reversion_timecode(self):
			return self.__reversion_timecode
		
		@property
		def timecode(self):
			return self.__timecode
		
		@property
		def timestamp(self):
			return datetime.datetime.fromtimestamp(os.path.getmtime(self.repository_file_path))
		
		def __setup(self):
			self.__is_reversion = False
			self.__reversion_timecode = None
			self.__timecode = None
			
			if self.key is None:
				return
			
			sections = self.key.split(".")
			if len(sections) >= 3:
				self.__timecode = sections[2]
				self.__reversion_timecode = self.__timecode
				if len(sections) >= 4:
					self.__is_reversion = True
					self.__reversion_timecode = sections[3]
	
	def __init__(self, path, parent=None):
		super().__init__(parent)
		self.__path = File.normalize(path)
		self.__repository_root = parent.repository_root 
		self.__setup()
	
	def __iter__(self):
		for ret in self.versions:
			yield ret
	
	def __str__(self):
		return self.path
	
	SUBEXTENSION_REPOSITORY = ".bb"
	
	@staticmethod
	def normalize(file_path):
		sections = path.explode(os.path.normpath(file_path).lower())
		for index in range(len(sections)):
			sections[index] = path.rstrippath(sections[index])
		return "/".join(sections)
	
	@property
	def current_version(self):
		return self.__current_version
	
	@property
	def directory(self):
		return self.__directory
	
	@property
	def extension(self):
		return self.__extension
	
	@property
	def last_version(self):
		ret = None
		for version in reversed(self.__versions):
			if version.is_reversion:
				continue
			ret = version
			break
		return ret
	
	@property
	def name(self):
		return self.__name
	
	@property
	def path(self):
		return self.__path
	
	@property
	def repository_directory(self):
		return self.__repository_directory
	
	@property
	def versions(self):
		return [*self.__versions]
	
	def find_version(self, timecode):
		if self.current_version is not None:
			if self.current_version.timecode == timecode:
				return self.current_version
		
		for version in self.__versions:
			if version.timecode == timecode:
				return version
		
		return None
	
	def restore(self, timecode):
		version = self.find_version(timecode)
		if version is None:
			return False
		
		if version.reversion_timecode is self.current_version.reversion_timecode:
			return False
		
		is_last = version.timecode == self.last_version.timecode
		timecode = datetime.datetime.now().strftime(File.__FORMAT_TIMECODE)
		key = f"{File.SUBEXTENSION_REPOSITORY}.{timecode}.{version.timecode}"
		file_name = self.name + key + self.extension
		file_path = self.repository_directory + file_name

		self.__current_version = self.Version(key, file_path)
		try:
			os.makedirs(self.repository_directory, exist_ok=True)
			if not is_last:
				shutil.copy2(version.repository_file_path, file_path)
			shutil.copy2(version.repository_file_path, self.path)
			
			while self.__versions:
				if not self.__versions[-1].is_reversion:
					break
				os.remove(self.__versions.pop().repository_file_path)
			
			if not is_last:
				self.__versions.append(self.__current_version)
		
		except Exception as ex:
			logging.error(f"{datetime.datetime.now()} ERROR: {ex}")
		
		self.__current_version = self.__versions[-1]
		return True
	
	def store(self):
		timecode = File.__generate_timecode(self.path)
		key = f"{File.SUBEXTENSION_REPOSITORY}.{timecode}"
		
		diff = int(timecode)
		if self.current_version is not None:
			diff -= int(self.current_version.timecode)
		
		version = self.find_version(timecode)
		if version is not None:
			if version is not self.current_version:
				return
			if diff == 0 or diff == 1:
				return
		
		file_name = self.name + key + self.extension
		file_path = self.repository_directory + file_name
		
		self.__current_version = self.Version(key, file_path)
		try:
			os.makedirs(self.repository_directory, exist_ok=True)
			shutil.copy2(self.path, file_path)
			
			if diff == 0 or diff == 1:
				current_version = self.__versions.pop()
				if diff:
					os.remove(current_version.repository_file_path)
			
			self.__versions.append(self.__current_version)
		
		except Exception as ex:
			logging.error(f"{datetime.datetime.now()} ERROR: {ex}")
		
		self.__current_version = self.__versions[-1]
	
	__FORMAT_TIMECODE = "%y%m%d%H%M"
	
	@staticmethod
	def __derepository(file_path):
		head, tail = path.lsplitpath(file_path)
		if head.endswith("/"):
			tail = head[-1] + tail
			head = head[:-1]
		if head.startswith("@"):
			head = head[1:] + ":"
		ret = head + tail
		return ret
	
	@staticmethod
	def __enrepository(file_path):
		head, tail = path.lsplitpath(file_path)
		if head.endswith("/"):
			tail = head[-1] + tail
			head = head[:-1]
		if head.endswith(":"):
			head = "@" + head[:-1]
		ret = head + tail
		return ret
	
	@staticmethod
	def __generate_timecode(file_path):
		ret = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).strftime(File.__FORMAT_TIMECODE)
		return ret
	
	def __setup(self):
		self.__directory, name = path.rsplitpath(self.path)
		self.__name, self.__extension = os.path.splitext(name)
		self.__repository_directory = path.normalize_dir_expression(self.__repository_root) + File.__enrepository(self.directory)
		self.__setup_versions()
	
	def __setup_versions(self):
		self.__current_version = None
		self.__versions = []
		pattern = fr"^{self.name}(\{File.SUBEXTENSION_REPOSITORY}\.\d+|\{File.SUBEXTENSION_REPOSITORY}\.\d+\.\d+){self.extension}$"
		
		if not os.path.isdir(self.repository_directory):
			return
		
		for file_name in os.listdir(self.repository_directory):
			m = re.match(pattern, file_name)
			if m:
				key = m.group(1)
				repository_file_path = path.implode(self.repository_directory, file_name)
				if os.path.isfile(repository_file_path):
					self.__current_version = self.Version(key, repository_file_path)
					self.__versions.append(self.__current_version)


class Work(QObject):
	"""
	file watch work
	"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.__setup()
	
	def __str__(self):
		return self.root
	
	nameChanged = Signal()
	recursiveChanged = Signal()
	rootChanged = Signal()
	
	@property
	def is_active(self):
		return self.__observer is not None
	
	@is_active.setter
	def is_active(self, value):
		if value == self.is_recursive:
			return
		
		if value:
			self.activate()
		else:
			self.deactivate()
	
	@property
	def is_recursive(self):
		return self.__is_recursive
	
	@is_recursive.setter
	def is_recursive(self, value):
		if value == self.is_recursive:
			return
		
		with self.__KeepActivity(self) as keep:
			self.__is_recursive = value
		
		self.recursiveChanged.emit()
	
	@property
	def name(self):
		return self.__name
	
	@name.setter
	def name(self, value):
		if value == self.name:
			return
		
		self.__name = value
		self.nameChanged.emit()
	
	@property
	def on_created_handler(self):
		return self.__common.on_created_handler
	
	@on_created_handler.setter
	def on_created_handler(self, value):
		self.__common.on_created_handler = value
	
	@property
	def on_deleted_handler(self):
		return self.__common.on_deleted_handler
	
	@on_deleted_handler.setter
	def on_deleted_handler(self, value):
		self.__common.on_deleted_handler = value
	
	@property
	def on_modified_handler(self):
		return self.__common.on_modified_handler
	
	@on_modified_handler.setter
	def on_modified_handler(self, value):
		self.__common.on_modified_handler = value
	
	@property
	def on_moved_handler(self):
		return self.__common.on_moved_handler
	
	@on_moved_handler.setter
	def on_moved_handler(self, value):
		self.__common.on_moved_handler = value
	
	@property
	def root(self):
		return self.__root
	
	@root.setter
	def root(self, value):
		if value == self.root:
			return
		
		with self.__KeepActivity(self) as keep:
			self.__is_recursive = False
			if value.endswith("..."):
				value = value[:-3]
				self.__is_recursive = True
			self.__root = Work.__normalize_root(value)
			self.name = os.path.basename(path.rstrippath(self.__root))
		
		self.rootChanged.emit()
	
	def activate(self):
		if self.is_active:
			return
		
		if not os.path.isdir(self.root):
			return
		
		app = self.parent()
		if self.is_recursive:
			for current_directory, directories, file_names in os.walk(self.root):
				for file_name in file_names:
					file_path = path.implode(current_directory, file_name)
					file = app.inquiry(file_path)
					if file.current_version is None:
						file.store()
		else:
			for file_name in os.listdir(self.root):
				file_path = path.implode(self.root, file_name)
				if os.path.isfile(file_path):
					file = app.inquiry(file_path)
					if file.current_version is None:
						file.store()
		
		handler = self.__Handler(self)
		
		self.__observer = Observer()
		self.__observer.schedule(handler, self.root, recursive=self.is_recursive)
		self.__observer.start()
	
	def deactivate(self):
		if not self.is_active:
			return
		
		self.__observer.stop()
		self.__observer.join()
		self.__observer = None
	
	def deserialize(self, desc, data):
		is_active = self.is_active
		if is_active:
			self.deactivate()
		
		self.root = desc
		
		if "is_active" in data:
			is_active = data["is_active"]
		
		if "is_recursive" in data:
			self.__is_recursive = data["is_recursive"]
		
		if is_active:
			self.activate()
	
	def serialize(self):
		ret = {
			"is_active" :		self.is_active,
			"is_recursive" :	self.is_recursive,
		}
		
		return ret
	
	@property
	def _common(self):
		return self.__common
	
	class __CommonData:
		def __init__(self):
			self.on_created_handler = None
			self.on_deleted_handler = None
			self.on_modified_handler = None
			self.on_moved_handler = None
	
	class __Handler(FileSystemEventHandler):
		def __init__(self, parent, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.__common = parent._common
		
		def on_created(self, event):
			if self.__common is None:
				return
			if self.__common.on_created_handler is None:
				return
			if not isinstance(event, FileCreatedEvent):
				return
			self.__common.on_created_handler(event)
		
		def on_deleted(self, event):
			if self.__common is None:
				return
			if self.__common.on_deleted_handler is None:
				return
			if not isinstance(event, FileDeletedEvent):
				return
			self.__common.on_deleted_handler(event)
		
		def on_modified(self, event):
			if self.__common is None:
				return
			if self.__common.on_modified_handler is None:
				return
			if not isinstance(event, FileModifiedEvent):
				return
			self.__common.on_modified_handler(event)
		
		def on_moved(self, event):
			if self.__common is None:
				return
			if self.__common.on_moved_handler is None:
				return
			if not isinstance(event, FileMovedEvent):
				return
			self.__common.on_moved_handler(event)
	
	class __KeepActivity:
		def __init__(self, work):
			self.__work = work
			self.__is_active = work.is_active
		
		def __enter__(self):
			if self.__is_active:
				self.__work.deactivate()
			return self
		
		def __exit__(self, ex_type, ex_value, trace):
			if self.__is_active:
				self.__work.activate()
			return True
	
	@staticmethod
	def __normalize_root(value):
		ret = value
		if ret != "":
			ret = path.normalize_dir_expression(ret)
		return ret
	
	def __setup(self):
		self.__common = self.__CommonData()
		self.__observer = None
		self.__root = ""
		self.__name = ""
		self.__is_recursive = False
