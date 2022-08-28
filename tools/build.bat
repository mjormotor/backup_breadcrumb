@rem /* --------------------------------
@rem   Build exe file with PyInstaller batch
@rem 
@rem  [Usage]
@rem  1. Run Visual Studio
@rem  2. Set "Python Environments" you like
@rem  3. "Open Command Prompt Here..." on this project
@rem  4. Run "tools\build" in the prompt
@rem -------------------------------- */

@cd /d %~dp0..\

@pyinstaller __main__.py --onefile --noconsole --icon=assets/app.ico --name=backup_breadcrumb.exe
@exit /b
