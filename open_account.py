import pathview_api_functions as pv

org = raw_input('Organization? ').rstrip()
# search org list here for org name.  None is an OK answer

partial_name = raw_input('Partial path name? ').rstrip()
# could list out partial paths here and allow user to choose

paths = pv.get_paths(pv.pvc, pv.user, pv.password, org_name=org)
paths2 = []
for path in paths:
    if partial_name in path.pathName:
        paths2.append(path)
pathNum = 0
for path in paths2:
    pathNum += 1
    print str(pathNum) + '\t' + path.pathName

pathChoice = True
while pathChoice:
    pathChoice = raw_input('Open which path? ').rstrip()
    try:
        pathCh = int(pathChoice)
        if pathCh <= pathNum:
            pv.open_web(pv.create_url_path(pv.pvc, paths2[pathCh-1]))
    except:
        if pathNum == 'q' or pathNum == 'Q' or pathNum == '':
            break


