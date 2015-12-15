import pathview_api_functions as pv
# //import collections
from operator import itemgetter

# Sort a list of dictionary objects by a key - case insensitive
# mylist = sorted(mylist, key=lambda k: k['name'].lower())

org = raw_input('Organization? ').rstrip()
# search org list here for org name.  None is an OK answer

partial_name = raw_input('Partial path name? ').rstrip()
# could list out partial paths here and allow user to choose

paths = pv.get_paths(pv.pvc, pv.user, pv.password, org_name=org)
paths2 = []
for path in paths:
    if partial_name in path.pathName:
        paths2.append(path)
#newlist = sorted(list_to_be_sorted, key=lambda k: k['name'])
# paths3 = sorted(paths2)
# mylist = sorted(mylist, key=itemgetter('name'))
paths3 = sorted(paths2, key=lambda k: k.pathName)
pathNum = 0
for path in paths3:
    pathNum += 1
    print str(pathNum) + '\t' + path.pathName

pathChoice = True
while pathChoice:
    pathChoice = raw_input('Open which path? ').rstrip()
    try:
        pathCh = int(pathChoice)
        if pathCh <= pathNum:
            pv.open_web(pv.create_url_path(pv.pvc, paths3[pathCh-1]))
    except:
        if pathNum == 'q' or pathNum == 'Q' or pathNum == '':
            break


