@rem /* --------------------------------
@rem   Convert qrc into python script file with PyInstaller batch
@rem 
@rem  [Usage]
@rem  1. Just double click this file
@rem -------------------------------- */

@cd /d %~dp0..\

@pyside6-rcc assets.qrc -o assets.py
@exit /b
