Author: Brian Spragge

This program is specifically for organizing or collapsing files
and/or folders in a given directory.  Either recursive or shallow
sort is possible.  Also, you can simplify the process with collapse
all, which will take all the files and files in folders in a given
directory and move them to a single file in the chosen directory.
All of the extra folders are deleted or moved to an empty folder
next to the files' folder.

Build: pyinstaller --clean --onefile --name DirO --contents-directory build main.py
