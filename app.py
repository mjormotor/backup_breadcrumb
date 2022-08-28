"""
/* --------------------------------
   Application main work

 - management of work.File objects
 - management of work.Work(target) objects
 - own the Window as file browser
 - own the resident tasktray icon
 - own icon and theme resources
 - process command line option and trace it by second more launch
-------------------------------- */
"""

from argparse import ArgumentParser
import datetime
import json
import logging
import os
import sys
import winreg

from PySide6.QtCore import QSettings, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
import qdarktheme

import assets
import forms
import path
from singleton import MultipleSingletonsError, Singleton
import work


class Application(QApplication):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.__setup()
	
	@property
	def config(self):
		return self.__config
	
	@property
	def icon(self):
		return self.__icon
	
	@property
	def log_file_path(self):
		return self.__log_file_path
	
	@log_file_path.setter
	def log_file_path(self, value):
		self.__log_file_path = value
	
	@property
	def palette(self):
		return self.__palette
	
	@property
	def repository_root(self):
		return self.__repository_root
	
	@repository_root.setter
	def repository_root(self, value):
		self.__repository_root = value
	
	@property
	def stylesheet(self):
		return self.__stylesheet
	
	@property
	def targets_file_path(self):
		return self.__targets_file_path
	
	@targets_file_path.setter
	def targets_file_path(self, value):
		self.__targets_file_path = value
	
	@property
	def window(self):
		return self.__window
	
	def add_target(self):
		ret = self.__create_target()
		self.__targets.append(ret)
		return ret
	
	def find_target(self, root):
		if root.endswith("..."):
			root = root[:-3]
		
		for target in self.__targets:
			if path.equals(target.root, root):
				return target
		
		return None
	
	def get_targets(self):
		for ret in self.__targets:
			yield ret
	
	def inquiry(self, file_path):
		ret = None
		if os.path.isfile(file_path):
			file_path = work.File.normalize(file_path)
			if file_path in self.__files:
				ret = self.__files[file_path]
			else:
				ret = work.File(file_path, self)
				self.__files[file_path] = ret
		
		return ret
	
	def move_target(self, from_, to):
		moved = self.__targets.pop(from_)
		self.__targets.insert(to, moved)
	
	def on_created(self, event):
		file_path = event.src_path
		if self.__is_in_repository(file_path):
			return
		logging.info(f"{datetime.datetime.now()} CREATED: {file_path}")
		file = self.inquiry(file_path)
		file.store()
	
	def on_deleted(self, event):
		file_path = event.src_path
		if self.__is_in_repository(file_path):
			return
		logging.info(f"{datetime.datetime.now()} DELETED: {file_path}")
	
	def on_modified(self, event):
		file_path = event.src_path
		if self.__is_in_repository(file_path):
			return
		logging.info(f"{datetime.datetime.now()} MODIFIED: {file_path}")
		file = self.inquiry(file_path)
		file.store()
	
	def on_moved(self, event):
		file_path = event.dest_path
		if self.__is_in_repository(file_path):
			return
		logging.info(f"{datetime.datetime.now()} MOVED_TO: {file_path}")
		file = self.inquiry(file_path)
		file.store()
	
	def process(self, argv):
		self.__show_window()
		
		arguments = " ".join(argv)
		logging.info(f"{datetime.datetime.now()} EXECUTE: {arguments}")
		
		if len(argv) > 1:
			args = self.__parser.parse_args(argv[1:])
			if args.remove_targets:
				self.__process_remove_targets(args.remove_targets)
			if args.add_targets:
				self.__process_add_targets(args.add_targets)
	
	def remove_target(self, target):
		self.__targets.remove(target)
		target.deactivate()
		target.deleteLater()
	
	def restore(self, config=None):
		config = self.__update_config(config)
		if config is None:
			return
		
		config.beginGroup("Application")
		
		repository_root = config.value("repository")
		if repository_root:
			self.__repository_root = repository_root
		
		targets_file_path = config.value("targets")
		if targets_file_path:
			self.__targets_file_path = targets_file_path
		
		log_file_path = config.value("log")
		if log_file_path:
			self.__log_file_path = log_file_path
		
		config.endGroup()
	
	def revert(self, target, ):
		self.__targets.remove(target)
		target.deactivate()
	
	def start(self):
		config = QSettings("config.ini", QSettings.IniFormat)
		self.restore(config)
		
		if self.log_file_path:
			logging.basicConfig(filename=self.log_file_path, encoding='utf-8', level=logging.INFO)
		
		self.__deserialize(self.targets_file_path)
		
		self.__tray_icon = self.__TrayIcon()
		self.__tray_icon.setIcon(self.icon)
		self.__tray_icon.add_menu(self.tr("Show"), self.__show_window)
		self.__tray_icon.add_menu(self.tr("Quit"), self.stop)
		self.__tray_icon.setVisible(True)
		self.__tray_icon.activated.connect(self.__on_icon_activated)
		
		self.__window = forms.create_window(self)
	
	def stop(self):
		self.__serialize(self.targets_file_path)
		for target in self.__targets:
			target.deactivate()
		
		self.store()
		
		if self.__window is not None:
			self.__window.close()
			self.__window = None
		
		self.__tray_icon.setVisible(False)
		self.__tray_icon = None
		
		if self.__config is not None:
			self.__config.sync()
		
		self.quit()
	
	def store(self, config=None):
		config = self.__update_config(config)
		if config is None:
			return
		
		config.beginGroup("Application")
		config.setValue("repository", self.__repository_root)
		config.setValue("targets", self.__targets_file_path)
		config.setValue("log", self.__log_file_path)
		config.endGroup()
	
	class __ArgumentParser(ArgumentParser):
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.__setup()
		
		def __setup(self):
			self.add_argument("-a", "--add", action="append", dest="add_targets", metavar="DIR_PATH",
								help="add new backup target")
			self.add_argument("-r", "--remove", action="append", dest="remove_targets", metavar="DIR_PATH",
								help="remove backup target")
	
	class __TrayIcon(QSystemTrayIcon):
		def __init__(self, *args, **kwargs):
			super().__init__(*args, **kwargs)
			self.__setup()
		
		def add_menu(self, text, action):
			ret = self.__menu.addAction(text)
			ret.triggered.connect(action)
			return ret
		
		def __setup(self):
			self.__menu = QMenu()
			self.setContextMenu(self.__menu)
	
	__dispatcher = Signal(list)
	
	__REG_PATH_THEMES_PERSONALIZE = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
	
	def __create_target(self):
		ret = work.Work(self)
		ret.on_created_handler = self.on_created
		ret.on_deleted_handler = self.on_deleted
		ret.on_modified_handler = self.on_modified
		ret.on_moved_handler = self.on_moved
		return ret
	
	def __deserialize(self, file_path):
		try:
			with open(file_path, "r") as file:
				data = json.load(file)
				for desc, value in data.items():
					target = self.__create_target()
					target.deserialize(desc, value)
					self.__targets.append(target)
		except Exception as ex:
			logging.error(f"{datetime.datetime.now()} ERROR: {ex}")
	
	def __is_in_repository(self, file_path):
		repository_root = os.path.abspath(self.__repository_root)
		repository_drive, repository_root = os.path.splitdrive(repository_root)
		file_path = os.path.abspath(file_path)
		file_drive, file_path = os.path.splitdrive(file_path)
		
		if file_drive.lower() != repository_drive.lower():
			return False
		
		return not os.path.relpath(file_path, repository_root).startswith("..")
	
	def __on_icon_activated(self, reason):
		if reason == QSystemTrayIcon.DoubleClick:
			self.__show_window()
	
	def __process_add_targets(self, descs):
		if self.window is None:
			return
		
		for desc in descs:
			self.window.add_target_page(desc)
	
	def __process_remove_targets(self, descs):
		if self.window is None:
			return
		
		for desc in descs:
			self.window.remove_target_page(desc)
	
	def __receive(self, arguments):
		self.__dispatcher.emit(arguments.split())
	
	def __serialize(self, file_path):
		data = {}
		for target in self.__targets:
			root = target.root
			if root:
				data[root] = target.serialize()
		
		try:
			with open(file_path, "w") as file:
				json.dump(data, file, indent=2)
		except Exception as ex:
			logging.error(f"{datetime.datetime.now()} ERROR: {ex}")
	
	def __setup(self):
		self.__singleton = Singleton()
		self.__config = None
		self.__repository_root = "repository"
		self.__targets_file_path = "target.json"
		self.__log_file_path = os.path.splitext(sys.argv[0])[0] + ".log"
		self.__window = None
		self.__targets = []
		self.__files = {}
		self.__icon = QIcon(":assets/app.ico")
		self.__parser = self.__ArgumentParser()
		self.__setup_os_is_darkmode()
		self.__stylesheet = qdarktheme.load_stylesheet("dark" if self.__os_is_darkmode else "light")
		self.__palette = qdarktheme.load_palette("dark" if self.__os_is_darkmode else "light")
		self.__dispatcher.connect(self.process)
		self.__singleton.trace(self.__receive)
		self.setStyleSheet(self.__stylesheet)
		self.setQuitOnLastWindowClosed(False)
	
	def __setup_os_is_darkmode(self):
		key = winreg.OpenKeyEx(winreg.HKEY_CURRENT_USER, self.__REG_PATH_THEMES_PERSONALIZE)
		value, regtype = winreg.QueryValueEx(key, "AppsUseLightTheme")
		winreg.CloseKey(key)
		self.__os_is_darkmode = value == 0
	
	def __show_window(self):
		if self.__window is not None:
			self.__window.open()
	
	def __update_config(self, config):
		if config is not None:
			self.__config = config
		return self.__config
