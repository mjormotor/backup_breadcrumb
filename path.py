"""
/* --------------------------------
   File path process utilities
-------------------------------- */
"""
def explode(file_path):
	ret = []
	tail = file_path
	while tail:
		head, tail = lsplitpath(tail)
		ret.append(head)
	return ret


def equals(lhs, rhs):
	lhs_sections = explode(lhs)
	rhs_sections = explode(rhs)
	section_count = len(lhs_sections)
	if len(rhs_sections) != section_count:
		return False
	
	for index in reversed(range(section_count)):
		lhs_section = rstrippath(lhs_sections[index]).lower()
		rhs_section = rstrippath(rhs_sections[index]).lower()
		if lhs_section != rhs_section:
			return False
	
	return True


def implode(*sections):
	ret = None
	if len(sections) > 0:
		ret = sections[0]
		for index in range(1, len(sections)):
			ret = normalize_dir_expression(ret)
			ret += sections[index]
	return ret


def is_dir_expression(file_path):
	if len(file_path) > 0:
		if file_path[-1] in "/\\":
			return True
	return False


def lsplitpath(file_path):
	for index, letter in enumerate(file_path):
		if letter == "/" or letter == "\\":
			return file_path[:index + 1], file_path[index + 1:]
	return file_path, ""


def normalize_dir_expression(file_path):
	ret = file_path
	if not is_dir_expression(ret):
		separator = "/" if ret.rfind("/") >= ret.rfind("\\") else "\\"
		ret += separator
	return ret


def rsplitpath(file_path):
	index = len(file_path)
	if file_path.endswith("/") or file_path.endswith("\\"):
		index -= 1
	while index > 0:
		letter = file_path[index - 1]
		if letter == "/" or letter == "\\":
			return file_path[:index], file_path[index:]
		index -= 1
	return file_path, ""


def rstrippath(file_path):
	index = len(file_path)
	while index > 0:
		letter = file_path[index - 1]
		if letter == "/" or letter == "\\":
			index -= 1
			continue
		return file_path[:index]
	return file_path
