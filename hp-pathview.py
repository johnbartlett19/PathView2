#TODO Add ability to find top ten paths with 1-day or 7-day violations (data not available in API) - now possible, see
 # Data get path data in swagger, can specify time window
#TODO Add ability to find paths with QoS violations (data not available in API)
# I think this is still missing
#TODO create path!!!!!!  using /v2/path second item in swagger
# Swagger at https://polycom.pathviewcloud.com/pvc-data/swagger
# TODO update routine that gets diagnostics using /v2/diagnostic API


import pathview_api_functions as pv, ip_address_functions as ip, time
import windows as w

pvc = 'https://hpq-appn-pca1.polycomrp.net'
user = 'John.Bartlett@Polycom.com'   # This one for all accounts
password = 'PolycomHDX'

org_file = 'org_codes_hp.txt'
global org_set
org_set = pv.Org_list(org_file)

def choose_org():
    find_org = raw_input('Organization? ').lower().rstrip()
    # search org list here for org name.  None is an OK answer
    possible = []
    for org in org_set.org_codes:
        if find_org in org.lower():
            possible.append(org)
    possible_sorted = sorted(possible)
    count = 0
    if len(possible_sorted) == 1:
        return possible_sorted[0]
    elif len(possible_sorted) == 0:
        print 'No match found'
        return None
    else:
        for org in possible_sorted:
            count += 1
            print count, org
        index = int(raw_input('Which org to use? '))
        return possible_sorted[index-1]

def choose_path(org):
    #https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2637&pathid=7971&startDate=1411171597714&endDate=1411258031465&loadSeqTz=false - 1411258634
    partial_name = raw_input('Partial path name? ').rstrip()
    end_sec = int(time.time())
    start_sec = end_sec - (24 * 60 * 60) # one day
    end = end_sec * 1000 # milliseconds
    start = start_sec * 1000 # milliseconds

    pv_user = user
    paths = pv.get_paths(pvc, pv_user, password, org_set, org_name=org)
    paths2 = []
    for path in paths:
        if partial_name.lower() in path.pathName.lower():
            paths2.append(path)
    paths3 = sorted(paths2, key=lambda k: k.pathName)
    if len(paths3) == 0:
        print 'No matching path found'
    elif len(paths3) > 1:
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
                    pv.open_web(pv.create_url_path(pvc, paths3[pathCh-1], start, end))
            except:
                if pathNum == 'q' or pathNum == 'Q' or pathNum == '' or pathNum == '0':
                    break
    else:
        pv.open_web(pv.create_url_path(pvc, paths3[0], start, end))

def choose_path_by_ip(org, pvc, user, password):
    #Query user for IP address
    ip_needed = raw_input('Target IP address? ').rstrip()
    # is this a straight IP address or a subnet query?
    # if '/' in ip_needed:
    #     is_subnet = True
    # else:
    #     is_subnet = False
    is_subnet = '/' in ip_needed
    if is_subnet:
        subnet = ip.Ip4Subnet(ip_needed, 'Subnet')
        #Find all paths in the org
        paths = pv.get_paths(pvc, user, password, org_set, org_name=org)
    else:
        paths = pv.get_paths(pvc, user, password, org_set, target=ip_needed)
    paths2 = []
    #Search thru looking for this IP address or subnet range
    for path in paths:
        # if path.ip == '10.252.0.30':
        #     asdf = 1
        if is_subnet:
            try:
                ip_decimal = ip.ipDDtoInt(path.ip)
                if ip_decimal > subnet.base and ip_decimal < subnet.top:
                    paths2.append(path)
            except:
                print 'Can not evaulate dest address ' + path.ip + ' , ignoring path.'
        else:
            if ip_needed == path.ip:
                paths2.append(path)
    paths3 = sorted(paths2, key=lambda k: k.pathName)
    if len(paths3) == 0:
        print 'No matching path found'
    elif len(paths3) > 1:
        pathNum = 0
        for path in paths3:
            pathNum += 1
            print str(pathNum) + '\t' + path.pathName + '\t' + path.ip
        pathChoice = True
        while pathChoice:
            pathChoice = raw_input('Open which path? ').rstrip()
            try:
                pathCh = int(pathChoice)
                if pathCh <= pathNum:
                    pv.open_web(pv.create_url_path(pvc, paths3[pathCh-1]))
            except:
                if pathNum == 'q' or pathNum == 'Q' or pathNum == '' or pathNum == '0':
                    break
    else:
        pv.open_web(pv.create_url_path(pvc, paths3[0]))

def path_param_exceeds(org, measure, threshold):
    all_paths = pv.get_paths(pvc, user, password, org_set, org_name=org)
    paths = []
    for path in all_paths:
        measures = pv.get_path_param(pvc, user, password, path, measure)
        for minute in measures:
            found = False
            for time_key in minute:
                if minute['value'] >= threshold:
                    paths.append(path)
                    found = True
                    break
            if found:
                break
    return paths

def open_diag():
    raise ValueError('Not defined')

def menu(options, org):
    print '\n'
    print 'Org:', org
    for key in sorted(options):
        print key + ':', options[key][0]

options = {
    '0': ['Exit'],
    '1': ['Choose an organization'],
    '2': ['Display a path in current org'],
    '3': ['Open diagnostics from deep link'],
    '4': ['Display path by IP address or CIDR subnet'],
    '5': ['Paths with loss in the last hour (slow)'],
    '6': ['Print all paths']
}

def printem(the_string):
    print the_string

org = None
while True:
    menu(options, org)
    choice = raw_input('\nChoice? ').strip()
    if choice == '0':
        break
    if choice == '1':
        org = choose_org()
        pv.open_org(org, org_set, pvc)
    if choice == '2':
        if org == None:
            org = choose_org()
        choose_path(org)
    if choice == '3':
        pv.open_diag_this_path_view(pvc, user, password)
    if choice == '4':
        choose_path_by_ip(org, pvc, user, password)
    if choice == '5':
        paths3 = path_param_exceeds(org, 'dataLoss', 1)
        pathNum = 0
        for path in paths3:
            pathNum += 1
            print str(pathNum) + '\t' + path.pathName + '\t' + path.ip
        pathChoice = True
        while pathChoice:
            pathChoice = raw_input('Open which path? ').rstrip()
            try:
                pathCh = int(pathChoice)
                if pathCh <= pathNum:
                    key_path = paths3[pathCh-1]
                    pv.open_web(pv.create_url_path(pvc, key_path))
            except:
                if pathNum == 'q' or pathNum == 'Q' or pathNum == '' or pathNum == '0':
                    break
            else:
                pv.open_web(pv.create_url_path(pvc, paths3[0]))
    if choice == '6':
        # pull all paths and print
        if org == None:
            org = choose_org()
        paths = pv.get_paths(pvc, user, password, org_set, org_name=org)
        filename = 'full_path_list.txt'
        pv.paths_to_file(paths, filename)
    if choice == '7':
        pv.check_orgs()
