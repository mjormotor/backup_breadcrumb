"""
/* --------------------------------
   Component widgets implementation

 - to keep single process to manage 1 of the repository
-------------------------------- */
"""
import os
import subprocess

from PySide6.QtCore import QDir, QEvent, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QAbstractItemView, QApplication, QComboBox, QFileSystemModel, QLineEdit, QMenu, QPushButton, QStyle, QStyledItemDelegate, QTabWidget, QTreeView, QWidget


class BreadcrumbNavigation(QWidget):
	"""
	woks like Breadcrumb control about filepath
	"""
	class Item(QPushButton):
		def __init__(self, parent=None):
			super().__init__(parent)
			self.__setup()
		
		@property
		def level(self):
			return self.__level
	
		@level.setter
		def level(self, value):
			self.__level = value
		
		def __on_clicked(self):
			self.parent().set_level(self.level)
		
		def __setup(self):
			self.__level = 0
			self.setFlat(True)
			self.clicked.connect(self.__on_clicked)
	
	def __init__(self, parent=None):
		super().__init__(parent)
		self.__common = _find_ancestor_common(parent)
		self.__setup()
	
	def set_level(self, level):
		self.__common.breadcrumb_level = level
	
	def setup(self):
		self.__common.target.recursiveChanged.connect(self.__reflect_target_recursive_changed)
		self.__reflect_target_recursive_changed()
	
	def __on_breadcrumb_changed(self):
		layout = self.layout()
		while layout.count() > 0:
			child = layout.takeAt(layout.count() - 1)
			item = child.widget()
			if item is None:
				continue
			item.deleteLater()
		
		for index, section in enumerate(self.__common.breadcrumb):
			item = self.Item(self)
			item.setText(section)
			item.level = index
			layout.addWidget(item)
		layout.addStretch()
	
	def __on_breadcrumb_level_changed(self):
		layout = self.layout()
		palette = self.window().application.palette
		count = layout.count()
		index = 0
		while index < count:
			if index > self.__common.breadcrumb_level:
				break
			child = layout.itemAt(index)
			item = child.widget()
			if item is None:
				return
			color = palette.color(QPalette.ColorRole.ButtonText).name(QColor.HexRgb)
			style_sheet = f"QPushButton	\
							{{	\
								color:	{color};	\
							}}"
			item.setStyleSheet(style_sheet)
			index += 1
		while index < count:
			item = layout.itemAt(index).widget()
			if item is None:
				return
			color = palette.color(QPalette.ColorRole.PlaceholderText).name(QColor.HexRgb)
			style_sheet = f"QPushButton	\
							{{	\
								color:	{color};	\
							}}"
			item.setStyleSheet(style_sheet)
			index += 1
	
	def __reflect_target_recursive_changed(self):
		if self.__common.target.is_recursive:
			self.show()
		else:
			self.hide()
	
	def __setup(self):
		self.__common.breadcrumbChanged.connect(self.__on_breadcrumb_changed)
		self.__common.breadcrumbLevelChanged.connect(self.__on_breadcrumb_level_changed)


class FilePathEdit(QLineEdit):
	"""
	acts like Windows file folder's path form, confirming needs enter, reset value on leaving
	"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.__setup()
	
	pathChanged = Signal()
	
	def eventFilter(self, widget, event):
		if event.type() == QEvent.FocusOut:
			self.resetText()
		return False
	
	def resetText(self):
		self.setText(self.__text)
	
	def __on_return_pressed(self):
		if self.text() == self.__text:
			return
		
		self.__text = self.text()
		self.pathChanged.emit()
	
	def __setup(self):
		self.__text = self.text()
		self.installEventFilter(self)
		self.returnPressed.connect(self.__on_return_pressed)


class FileTreeView(QTreeView):
	"""
	acts like Windows file folder's tree contol on left side
	"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.__setup()
	
	def filePath(self, index):
		return self.model().filePath(self.item(index))
	
	def item(self, index):
		return self.model().index(index.row(), 0, index.parent())
	
	def __setup(self):
		model = QFileSystemModel(self)
		model.setFilter(QDir.Dirs | QDir.NoDotAndDotDot)
		index = model.setRootPath(model.myComputer())
		self.setModel(model)
		self.setRootIndex(index)
		self.setHeaderHidden(True)
		for index in range(1, model.columnCount()):
			self.hideColumn(index)


class TabWidget(QTabWidget):
	"""
	appends add tab button
	"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.__setup()
	
	def openButton(self):
		return self.__open_button
	
	def __setup(self):
		self.__open_button = QPushButton("+", self)
		self.__open_button.setFixedSize(QSize(27, 22))
		self.__open_button.setFlat(False)
		self.setCornerWidget(self.__open_button)


class TargetRootEdit(FilePathEdit):
	"""
	attached folder open button and recursive switch
	"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.__common = _find_ancestor_common(parent)
		self.__setup()
	
	@property
	def target(self):
		return self.__common.target
	
	@target.setter
	def target(self, value):
		self.__common.target = value
	
	def setup(self):
		self.target.rootChanged.connect(self.__reflect_target_root)
		self.__reflect_target_root()
		self.target.recursiveChanged.connect(self.__reflect_target_is_recursive)
		self.__reflect_target_is_recursive()
	
	def sizeHint(self):
		ret = super().sizeHint()
		ret.setWidth(max(self.__directory_button.size().width() + self.__recursive_button.size().width(), ret.width()))
		return ret
	
	def resizeEvent(self, event):
		super().resizeEvent(event)
		geometry = self.__recursive_button.geometry()
		geometry.moveRight(self.size().width() - 1)
		self.__recursive_button.setGeometry(geometry)
	
	def __on_directory_button_clicked(self):
		_explore(self.target.root)
	
	def __on_recursive_button_clicked(self):
		self.target.is_recursive = not self.target.is_recursive
	
	def __on_path_changed(self):
		file_path = self.text()
		if file_path == "":
			self.target.deactivate()
			self.target.root = file_path
		elif os.path.isdir(file_path):
			self.target.root = file_path
			self.target.activate()
		else:
			self.resetText()
	
	def __reflect_target_root(self):
		root = self.target.root
		self.setText(root)
		if root == "":
			self.__recursive_button.hide()
		elif os.path.isdir(root):
			self.__recursive_button.show()
	
	def __reflect_target_is_recursive(self):
		self.__recursive_button.setChecked(self.target.is_recursive)
	
	def __setup(self):
		length = self.size().height() - 4
		
		directory_icon = QApplication.style().standardIcon(QStyle.SP_DirLinkIcon)
		self.__directory_button = QPushButton(self)
		self.__directory_button.setIcon(directory_icon)
		self.__directory_button.setFlat(True)
		self.__directory_button.setFixedSize(QSize(length, length))
		self.__directory_button.setCursor(Qt.ArrowCursor)
		self.__directory_button.clicked.connect(self.__on_directory_button_clicked)
		
		self.__recursive_button = QPushButton(self)
		self.__recursive_button.setCheckable(True)
		self.__recursive_button.setText("...")
		self.__recursive_button.setFlat(False)
		self.__recursive_button.setFixedSize(QSize(length, length))
		self.__recursive_button.setCursor(Qt.ArrowCursor)
		self.__recursive_button.clicked.connect(self.__on_recursive_button_clicked)

		palette = self.window().application.palette
		checked_color = palette.color(QPalette.ColorRole.HighlightedText).name(QColor.HexRgb)
		checked_background_color = palette.color(QPalette.ColorRole.Highlight).name(QColor.HexRgb)
		style_sheet = f"QPushButton	\
						{{	\
							border-radius:	4px;	\
							border-width:	1px;	\
							border-color:	{checked_background_color};	\
							padding:		2px;	\
						}}	\
						QPushButton:checked	\
						{{	\
							background-color:	{checked_background_color};	\
							color:				{checked_color};	\
						}}"
		self.__recursive_button.setStyleSheet(style_sheet)
		
		geometry = self.__recursive_button.geometry()
		geometry.moveRight(self.parent().size().width())
		self.__recursive_button.setGeometry(geometry)
		
		margins = self.textMargins()
		margins.setLeft(self.__directory_button.size().width())
		margins.setRight(self.__recursive_button.size().width())
		self.setTextMargins(margins)
		
		self.pathChanged.connect(self.__on_path_changed)


class TargetTreeView(QTreeView):
	"""
	browsed folder contents and their version controller
	"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.__common = _find_ancestor_common(parent)
		self.__setup()
	
	@property
	def column_sizes(self):
		return self.__common.column_sizes
	
	@property
	def current_path(self):
		return self.__common.breadcrumb_path
	
	@property
	def target(self):
		return self.__common.target
	
	@target.setter
	def target(self, value):
		self.__common.target = value
	
	def filePath(self, index):
		return self.model().filePath(self.item(index))
	
	def item(self, index):
		return self.model().index(index.row(), 0, index.parent())
	
	def paintEvent(self, event):
		super().paintEvent(event)
		header = self.header()
		for index in range(header.count()):
			self.resizeColumnToContents(index)
		
		if not self.__is_shown:
			self.__is_shown = True
			self.header().sectionResized.connect(self.__on_header_section_resized)
	
	def setup(self):
		self.target.rootChanged.connect(self.__update_model)
		self.target.recursiveChanged.connect(self.__update_model)
		self.__update_model()
	
	def sizeHintForColumn(self, column):
		if column >= len(self.column_sizes) - 1:
			return super().sizeHintForColumn(column)
		return self.column_sizes[column]
	
	class __DirectoryModel(QFileSystemModel):
		def __init__(self, parent=None):
			super().__init__(parent)
		
		def flags(self, index):
			ret = super().flags(index)
			if index.isValid():
				if index.column() == super().columnCount() - 1:
					ret |= Qt.ItemIsEditable
			
			return ret
		
		def hasChildren(self, parent):
			return self.filePath(parent) == self.rootPath()
		
		def headerData(self, section, orientation, role=Qt.DisplayRole):
			ret = None
			if section == super().columnCount() - 1:
				if role == Qt.DisplayRole:
					ret = self.tr("Version")
				elif role == Qt.DecorationRole:
					ret = self.parent().window().application.icon
				else:
					ret = super().headerData(section, orientation, role)
			
			if ret is None:
				ret = super().headerData(section, orientation, role)
			
			return ret
	
	class __ItemDelegate(QStyledItemDelegate):
		def __init__(self, parent=None):
			super().__init__(parent)
		
		def createEditor(self, parent, option, index):
			ret = None
			if index.isValid():
				if index.column() == self.parent().header().count() - 1:
					ret = self.__ComboBoxCell(parent)
					file_path = self.parent().filePath(index)
					file = self.parent().window().application.inquiry(file_path)
					for version in reversed(file.versions):
						if version.is_reversion:
							continue
						ret.addItem(version.timestamp.strftime("%Y/%m/%d %H:%M"), version)
			
			if ret is None:
				ret = super().createEditor(parent, option, index)
			
			return ret
		
		def setEditorData(self, editor, index):
			if index.isValid():
				if index.column() == self.parent().header().count() - 1:
					file_path = self.parent().filePath(index)
					file = self.parent().window().application.inquiry(file_path)
					if file.current_version.is_reversion:
						version = file.find_version(file.current_version.reversion_timecode)
						if version:
							position = editor.findData(version)
							if position != -1:
								editor.setCurrentIndex(position)
								return
			
			super().setEditorData(editor, index)
		
		def setModelData(self, editor, model, index):
			if index.isValid():
				if index.column() == self.parent().header().count() - 1:
					file_path = self.parent().filePath(index)
					file = self.parent().window().application.inquiry(file_path)
					version = editor.currentData()
					if version:
						file.restore(version.timecode)
						return
			
			super().setModelData(editor, model, index)
		
		class __ComboBoxCell(QComboBox):
			def __init__(self, parent=None):
				super().__init__(parent)
				self.__setup()
			
			def __setup(self):
				style_sheet = f"QComboBox	\
								{{	\
									padding:	0px;	\
								}}	\
								QLineEdit	\
								{{	\
									margin:		0px;	\
									padding:	0px;	\
								}}"
				self.setStyleSheet(style_sheet)
	
	def __build_context_menu(self, position):
		self.__context_menu.exec_(self.viewport().mapToGlobal(position))
	
	def __execute(self):
		for index in self.selectedIndexes():
			file_path = self.filePath(index)
			self.__execute_core(file_path)
			break
	
	def __execute_core(self, file_path):
		if os.path.isfile(file_path):
			self.__start(file_path)
		elif os.path.isdir(file_path):
			self.__common.push_breadcrumb(os.path.basename(file_path))
	
	def __explore(self):
		for index in self.selectedIndexes():
			_explore(self.filePath(index), True)
			break
	
	def __on_double_clicked(self, index):
		if index.column() == self.header().count() - 1:
			return
		
		file_path = self.filePath(index)
		self.__execute_core(file_path)
	
	def __on_header_section_resized(self, column, oldsize, newsize):
		header = self.header()
		for index in range(header.count()):
			size = header.sectionSize(index)
			if len(self.column_sizes) == index:
				self.column_sizes.append(size)
			else:
				self.column_sizes[index] = size
	
	def __setup(self):
		self.__is_shown = False
		self.__setup_context_menu()
		
		self.setItemDelegate(self.__ItemDelegate(self))
		self.setEditTriggers(self.editTriggers() | QAbstractItemView.SelectedClicked)
		
		self.doubleClicked.connect(self.__on_double_clicked)
		self.__common.breadcrumbChanged.connect(self.__update_model)
		self.__common.breadcrumbLevelChanged.connect(self.__update_model)
		
		self.sortByColumn(0, Qt.AscendingOrder)
		self.setContextMenuPolicy(Qt.CustomContextMenu)
		self.customContextMenuRequested.connect(self.__build_context_menu)
	
	def __setup_context_menu(self):
		self.__context_menu = QMenu()
		
		action = self.__context_menu.addAction(self.tr("Execute"))
		action.triggered.connect(self.__execute)

		action = self.__context_menu.addAction(self.tr("Show in explorer"))
		action.triggered.connect(self.__explore)
	
	def __start(self, path):
		# explorer would choke on forward slashes
		path = os.path.normpath(path)
	
		if os.path.isdir(path):
			subprocess.run(f"{__FILEBROWSER_PATH} \"{path}\"")
		elif os.path.isfile(path):
			subprocess.run(f"\"{path}\"", shell=True)
	
	def __update_model(self):
		model = self.__DirectoryModel(self)
		index = model.setRootPath(self.current_path)
		self.setModel(model)
		self.setRootIndex(index)
		if not self.target.is_recursive:
			model.setFilter(QDir.Files)


class TargetWidget(TabWidget):
	"""
	tabs container
	"""
	def __init__(self, parent=None):
		super().__init__(parent)
		self.__setup()
	
	@property
	def add_target_handler(self):
		return self.__add_target_handler
	
	@add_target_handler.setter
	def add_target_handler(self, value):
		self.__add_target_handler = value
	
	@property
	def target_tree_column_sizes(self):
		return self.__target_tree_column_sizes
	
	@property
	def page_class(self):
		return self.__page_class
	
	@page_class.setter
	def page_class(self, value):
		self.__page_class = value
	
	@property
	def remove_target_handler(self):
		return self.__remove_target_handler
	
	@remove_target_handler.setter
	def remove_target_handler(self, value):
		self.__remove_target_handler = value
	
	def addPage(self, target=None):
		if target is None:
			target = self.window().application.add_target()
		ret = self.__create_page(target)
		if ret is not None:
			target.nameChanged.connect(self.__on_target_name_changed)
			index = self.addTab(ret, target.name)
			self.setCurrentIndex(index)
		return ret
	
	def closeTab(self, index):
		widget = self.widget(index)
		if isinstance(widget, self.__page_class):
			return self.removePage(widget)
		return self.removeTab(index)
	
	def findPage(self, target):
		for index in range(self.count()):
			widget = self.widget(index)
			if isinstance(widget, self.__page_class):
				if widget.target == target:
					return widget
		return None
	
	def removePage(self, page):
		index = self.indexOf(page)
		page.target.nameChanged.disconnect(self.__on_target_name_changed)
		self.window().application.remove_target(page.target)
		return super().removeTab(index)
	
	def __create_page(self, target):
		if self.__page_class is None:
			return None
		ret = self.__page_class(self)
		ret.target = target
		ret.setup()
		return ret
	
	def __on_tab_bar_moved(self, from_, to):
		widget = self.widget(to)
		if not isinstance(widget, self.__page_class):
			return
		
		for index in range(max(from_, to)):
			if not isinstance(self.widget(index), self.__page_class):
				if from_ > index:
					from_ -= 1
				if to > index:
					to -= 1
		
		if from_ == to:
			return
		
		self.window().application.move_target(from_, to)
	
	def __on_target_name_changed(self):
		index = self.currentIndex()
		self.setTabText(index, self.currentWidget().target.name)
	
	def __setup(self):
		self.__target_tree_column_sizes = []
		self.__add_target_handler = None
		self.__page_class = None
		self.tabCloseRequested.connect(self.closeTab)
		self.tabBar().tabMoved.connect(self.__on_tab_bar_moved)
		self.openButton().clicked.connect(lambda: self.addPage())


__FILEBROWSER_PATH = os.path.join(os.getenv("WINDIR"), "explorer.exe")


def _find_ancestor_common(parent):
	while parent:
		if hasattr(parent, "_common"):
			return parent._common
		parent = parent.parent()
	return None

	
def _explore(path, select=False):
	# explorer would choke on forward slashes
	if path:
		path = os.path.normpath(path)
		if os.path.isfile(path):
			select = True
		if select:
			subprocess.run(f"{__FILEBROWSER_PATH} /select \"{path}\"")
		else:
			subprocess.run(f"{__FILEBROWSER_PATH} \"{path}\"")
	else:
		subprocess.run(f"{__FILEBROWSER_PATH}")
