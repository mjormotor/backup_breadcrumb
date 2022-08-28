"""
/* --------------------------------
   Program entry point
-------------------------------- */
"""
import os
import sys

from app import Application, MultipleSingletonsError


try:
	# execute on the directory has .exe
	os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
	
	instance = Application()
	instance.start()
	
	# process command line option
	instance.process(sys.argv)
	
	# start resident process
	sys.exit(instance.exec())

except MultipleSingletonsError:
	# launched as second more process
	# so just post command line options to the first process
	# and immediatly exit
	sys.exit(-1)
