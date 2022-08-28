"""
/* --------------------------------
   Forms implementation

 - there are form definitions that use QUiLoader to load .ui files
 - to keep valid reference direction thought of using PyUic, split widget classes om .ui file (forms -> ui_forms -> widgets)
-------------------------------- */
"""

import os
import sys

from PySide6.QtCore import QFile, QObject
from PySide6.QtGui import QIcon
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QMainWindow, QSplitter, QVBoxLayout, QWidget

import assets
import path
from widgets import *


_name = os.path.splitext(os.path.basename(__file__))[0]
_module = sys.modules[_name]


class UiLoader(QUiLoader):
	"""
	enhanced about file management
	"""
	def __init__(self, parent: QObject=None):
		super().__init__()
		self.__parent = parent
	
	def load(self, file_path: str):
		with self.__File(file_path) as ui_file:
			return super().load(ui_file, parentWidget=self.__parent)
	
	class __File(QFile):
		def __init__(self, file_path: str, mode=QFile.ReadOnly):
			super().__init__(file_path)
			self.__mode = mode
		
		def __enter__(self):
			self.open(self.__mode)
			return self
		
		def __exit__(self, ex_type, ex_value, trace):
			return self.close()


class PageView(QWidget):
	"""
	tabbed page contents
	"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.__setup()
	
	NAVIGATION = "Navigation"
	TARGET_ROOT = "TargetRoot"
	TARGET_VIEW = "TargetView"
	
	@property
	def navigation(self):
		if self.__navigation is None:
			self.__navigation = self.findChild(BreadcrumbNavigation, PageView.NAVIGATION)
		return self.__navigation
	
	@property
	def target(self):
		return self.__common.target
	
	@target.setter
	def target(self, value):
		self.__common.target = value
	
	@property
	def target_root(self):
		if self.__target_root is None:
			self.__target_root = self.findChild(TargetRootEdit, PageView.TARGET_ROOT)
		return self.__target_root
	
	@property
	def target_view(self):
		if self.__target_view is None:
			self.__target_view = self.findChild(TargetTreeView, PageView.TARGET_VIEW)
		return self.__target_view
	
	@classmethod
	def create(cls, parent=None):
		return cls(parent=parent)
	
	def setup(self):
		self.navigation.setup()
		self.target_root.setup()
		self.target_view.setup()
	
	@property
	def _common(self):
		return self.__common
	
	class __CommonData(QObject):
		def __init__(self, parent=None):
			super().__init__(parent)
			self.column_sizes = None
			self.__setup()
		
		breadcrumbChanged = Signal()
		breadcrumbLevelChanged = Signal()
		
		@property
		def breadcrumb(self):
			for ret in self.__breadcrumb:
				yield ret
		
		@property
		def breadcrumb_level(self):
			return self.__breadcrumb_level
		
		@breadcrumb_level.setter
		def breadcrumb_level(self, value):
			if value == self.__breadcrumb_level:
				return
			
			self.__breadcrumb_level = value
			self.breadcrumbLevelChanged.emit()
		
		@property
		def breadcrumb_path(self):
			ret = self.target.root
			for level in range(1, len(self.__breadcrumb)):
				if level > self.breadcrumb_level:
					break
				ret = path.implode(ret, self.__breadcrumb[level])
			return ret
		
		@property
		def target(self):
			return self.__target
		
		@target.setter
		def target(self, value):
			if value == self.__target:
				return
			
			if self.__target:
				self.__target.recursiveChanged.disconnect(self.__reset_breadcrumb)
				self.__target.rootChanged.disconnect(self.__reset_breadcrumb)
			self.__target = value
			if self.__target:
				self.__target.recursiveChanged.connect(self.__reset_breadcrumb)
				self.__target.rootChanged.connect(self.__reset_breadcrumb)
			self.__reset_breadcrumb()
		
		def push_breadcrumb(self, value):
			if self.__breadcrumb_level < len(self.__breadcrumb) - 1:
				if value == self.__breadcrumb[self.__breadcrumb_level + 1]:
					self.__breadcrumb_level += 1
					self.breadcrumbLevelChanged.emit()
					return
				self.__breadcrumb = self.__breadcrumb[:self.__breadcrumb_level + 1]
			self.__breadcrumb.append(value)
			self.__breadcrumb_level = len(self.__breadcrumb) - 1
			self.breadcrumbChanged.emit()
		
		def __reset_breadcrumb(self):
			self.__breadcrumb.clear()
			if self.__target:
				head, tail = path.rsplitpath(self.target.root)
				self.__breadcrumb.append(path.rstrippath(tail))
			self.__breadcrumb_level = 0
			self.breadcrumbChanged.emit()
		
		def __setup(self):
			self.__target = None
			self.__breadcrumb = []
			self.__breadcrumb_level = 0
	
	class __UiLoader(UiLoader):
		def createWidget(self, className, parent=None, name=""):
			if className == "BreadcrumbNavigation":
				ret = BreadcrumbNavigation(parent)
				ret.setObjectName(name)
			elif className == "TargetRootEdit":
				ret = TargetRootEdit(parent)
				ret.setObjectName(name)
			elif className == "TargetTreeView":
				ret = TargetTreeView(parent)
				ret.setObjectName(name)
			else:
				ret = super().createWidget(className, parent, name)
			return ret
	
	def __setup(self):
		self.__common = self.__CommonData()
		if isinstance(self.parent(), TargetWidget):
			self.__common.column_sizes = self.parent().target_tree_column_sizes
		self.__navigation = None
		self.__target_root = None
		self.__target_view = None
		
		loader = self.__UiLoader(self)
		self._ui = loader.load(":assets/page.ui")
		
		layout = QVBoxLayout()
		layout.addWidget(self._ui)
		self.setLayout(layout)


class Window(QMainWindow):
	"""
	main window as the file browser
	"""
	def __init__(self, app, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.__application = app
		self.__setup()
	
	FILE_TREE = "FileTree"
	SPLITTER = "Splitter"
	TARGET_PAGES = "TargetPages"
	
	instance = None
	
	@property
	def file_tree(self):
		if self.__file_tree is None:
			self.__file_tree = self.findChild(FileTreeView, Window.FILE_TREE)
		return self.__file_tree
	
	@property
	def splitter(self):
		if self.__splitter is None:
			self.__splitter = self.findChild(QSplitter, Window.SPLITTER)
		return self.__splitter
	
	@property
	def target_pages(self):
		if self.__target_pages is None:
			self.__target_pages = self.findChild(TabWidget, Window.TARGET_PAGES)
		return self.__target_pages
	
	@property
	def ui(self):
		return self._ui
	
	@property
	def application(self):
		return self.__application
	
	@classmethod
	def create(cls, app, parent=None):
		if cls.instance is None:
			cls.instance = cls(app, parent=parent)
		return cls.instance
	
	def add_target_page(self, desc):
		ret = None
		target = self.application.find_target(desc)
		if target:
			ret = self.target_pages.findPage(target)
			if ret:
				self.target_pages.setCurrentIndex(self.target_pages.indexOf(ret))
		else:
			target = self.application.add_target()
			target.root = desc
			target.activate()
			ret = self.target_pages.addPage(target)
		return ret
	
	def closeEvent(self, event):
		self.store()
		self.hide()
		event.ignore()
	
	def open(self):
		self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
		self.show()
		self.activateWindow()
	
	def remove_target_pages(self, desc):
		target = self.application.find_target(desc)
		if target:
			page = self.target_pages.findPage(target)
			if page:
				self.target_pages.removePage(page)
	
	def restore(self, config=None):
		config = self.__update_config(config)
		if config is None:
			return
		
		# restoration window size, position and other states
		config.beginGroup("Window")
		geometry = config.value("geometry")
		if geometry:
			self.restoreGeometry(geometry)
		window_state = config.value("window_state")
		if window_state:
			self.restoreState(window_state)
		splitter_state = config.value("splitter_state")
		if splitter_state:
			self.splitter.restoreState(splitter_state)
		target_tree_column_sizes = config.value("target_tree_column_sizes")
		if target_tree_column_sizes:
			for index in range(len(target_tree_column_sizes)):
				target_tree_column_sizes[index] = int(target_tree_column_sizes[index])
			self.target_pages.target_tree_column_sizes.clear()
			self.target_pages.target_tree_column_sizes.extend(target_tree_column_sizes)
		config.endGroup()
		
		config.beginGroup("Targets")
		active_target = config.value("active_target")
		if active_target:
			self.target_pages.setCurrentIndex(int(active_target))
		config.endGroup()
	
	def store(self, config=None):
		config = self.__update_config(config)
		if config is None:
			return
		
		# save window size, position and other states
		config.beginGroup("Window")
		config.setValue("geometry", self.saveGeometry())
		config.setValue("window_state", self.saveState())
		config.setValue("splitter_state", self.splitter.saveState())
		config.setValue("target_tree_column_sizes", self.target_pages.target_tree_column_sizes)
		config.endGroup()
		
		config.beginGroup("Targets")
		config.setValue("active_target", self.target_pages.currentIndex())
		config.endGroup()
	
	class __UiLoader(UiLoader):
		def createWidget(self, className, parent=None, name=""):
			if className == "TargetWidget":
				ret = TargetWidget(parent)
				ret.setObjectName(name)
			elif className == "FileTreeView":
				ret = FileTreeView(parent)
				ret.setObjectName(name)
			else:
				ret = super().createWidget(className, parent, name)
			return ret
	
	def __add_target_directly(self, index):
		for index in self.file_tree.selectedIndexes():
			file_path = self.file_tree.filePath(index)
			page = self.add_target_page(file_path)
			page.target.is_recursive = False
			break
	
	def __add_target_recursively(self, index):
		for index in self.file_tree.selectedIndexes():
			file_path = self.file_tree.filePath(index)
			page = self.add_target_page(file_path + "...")
			page.target.is_recursive = True
			break
	
	def __build_file_tree_context_menu(self, position):
		self.__file_tree_context_menu.exec_(self.file_tree.viewport().mapToGlobal(position))
	
	def __on_file_tree_double_clicked(self, index):
		file_path = self.file_tree.filePath(index)
		self.add_target_page(file_path)
	
	def __setup(self):
		self.__file_tree = None
		self.__splitter = None
		self.__target_pages = None
		self.__config = None
		self.__setup_file_tree_context_menu()
		self.setWindowIcon(QIcon(":assets/app.ico"))
		self.setWindowTitle("Backup Breadcrumb")
		
		loader = self.__UiLoader(self)
		self._ui = loader.load(":assets/window.ui")
		self.setCentralWidget(self._ui)
		
		self.file_tree.setContextMenuPolicy(Qt.CustomContextMenu)
		self.file_tree.customContextMenuRequested.connect(self.__build_file_tree_context_menu)
		self.file_tree.doubleClicked.connect(self.__on_file_tree_double_clicked)
		self.splitter.setSizes((100,300))
		
		self.target_pages.page_class = PageView
		for target in self.application.get_targets():
			self.target_pages.addPage(target)
		
		if self.target_pages.count() == 0:
			self.target_pages.addPage()
	
	def __setup_file_tree_context_menu(self):
		self.__file_tree_context_menu = QMenu()
		
		action = self.__file_tree_context_menu.addAction(self.tr("Backup this directory recursively"))
		action.triggered.connect(self.__add_target_recursively)
		
		action = self.__file_tree_context_menu.addAction(self.tr("Backup this directory directly"))
		action.triggered.connect(self.__add_target_directly)
	
	def __update_config(self, config):
		if config is not None:
			self.__config = config
		return self.__config


def create_window(app):
	if _module.Window.instance is None:
		ret = Window.create(app)
		ret.restore(app.config)
		ret.show()
		_module.Window.instance = ret
	else:
		ret = _module.Window.instance
		ret.raise_()
	
	return ret
