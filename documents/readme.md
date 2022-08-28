# Backup Breadcrumb

## Overview
* This software makes the backup system work on targeted directories.
* This software saves a copy of the file to the repository each time a file in the target directory is updated during running. 
* The file browser interface represents the backup target and allows manipulation of individual file versions.

## Cautions
* This software is a so-called resident application so you should select the "Quit" menu on tasktray icon to stop backup work instead of closing the file browser.
* Files are stored in the repository as-is copies, that causes easily capacity explosion of the repository when large numbers of large files are updated large times.
* It is intended to operate as a temporary incremental save function on a local machine for a few directories currently being worked in process, and then it is expected to the finished files will be maintained in the main version control system and the used repository will be discarded.
