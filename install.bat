REM for installing components needed for PathView scripts
REM This is incomplete and not tested

REM Download python here:
ECHO Download python here:
ECHO This has not been updated to reflect python3 usage, but code has been updated
ECHO https://www.python.org/ftp/python/2.7.11/python-2.7.11.msi
REM Set user path to include python
set PATH=%PATH%;C:\Python27

REM Ensure we have the latest pip for installation
REM C:\Python27\python -m pip install -U pip setuptools
C:\Python27\python -m pip install --upgrade pip

REM Need this for certs:
C:\Python27\python -m pip install certifi

REM For calling APIs
C:\Python27\python -m pip install urllib3

REM Set path variable for python
setx PATH "%PATH%;C:\Python27"

