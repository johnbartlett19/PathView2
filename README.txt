This is a Python program that provides a command line interface into the PathView cloud.  It is useful
for quickly getting to the right PathView organization, and finding the paths of interest.  It will then
open specific paths for you in your default web browser.

Files:
create_paths.xlsx and create_paths.csv:  These files are used if you want to create paths using this tool.  Start with
the create_paths.xlsx file. Leave the header line as it is, delete the example data, and fill in the fields to specify
the information about the paths to be created.  Save your file into this directory.  Then save-as a CSV file to create
the create_paths.csv file.  You can save under a different name to distinguish different jobs (e.g. customer-xyz.csv).
When using the program, it will list out all the CSV files in this directory and allow you to choose the correct one.

ip_address.py:  not being used

ip_address_functions.py:  This is a set of routines used by the program to manipulate IP addresses

pathview.py:  This is the main program

pathview_api_functions.py:  This is a set of routines to create the classes and provide the needed functions to access
the cloud APIs and to open web pages in the local browser

user.txt:  The program looks for this file to get the URL of the cloud (e.g. https://polycom.pathviewcloud.com) and the
users login credentials.  If this file is not present, the program will ask for these three items (url, login, password)
when it starts.  user.txt.example shows the required format for this file.  If you want to store this information to
simplify the use of the tool, modify user.txt.example and save it as user.txt.  Note that the first time the program
opens a web page you will still have to sign-in to the cloud with credentials on the web page as well.  The credentials
in this file are used for the API Get and Post functions only.

windows.py:  This file provides a set of routines for opening windows on the desktop, such as the one that is opened
to paste in a deep-link when searching for diagnostic reports.

run_in_idle.bat:  If you run this bat file it will open the pathview script in the Idle interpreter.  You can then run
the program by hitting the F5 key.  If there are bugs that cause the program to quit, this will allow you to see the
error output and send me a screen shot or text capture so I can figure out what is going on.

Using the program:

1) You need a python environment.  This program is written for Python version 2.7.  Download a copy of Python from here:
https://www.python.org/download/releases/2.7/
This link is for the Windows MSI package:
https://www.python.org/ftp/python/2.7.11/python-2.7.11.msi

2) Additional modules are needed to run this program.  These can be installed using the install.bat file in this
directory.

3) Create the user.txt file with your credentials (see notes above on user.txt)

4) Double-click the pathview.py file to start.  You can put a link to this on your desktop or some other convenient place

