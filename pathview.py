#TODO Fixed urllib3 and credentials for get_paths, extend to other requests
#TODO Add ability to find top ten paths with 1-day or 7-day violations
#TODO Add ability to find paths with QoS violations
#TODO Test pulling orgs as other than super user
#TODO Track input from web server up through urllib

import pathview_api_functions as pv, ip_address_functions as ip, time, os, csv
import glob

def choose_org():
    find_org = raw_input('Fragment of organization name? ').lower().rstrip()
    # search org list here for org name.  None is an OK answer
    possible = []
    for org in org_set:
        if find_org in org.name.lower():
            possible.append(org)
    possible_sorted = sorted(possible)
    count = 0
    if len(possible_sorted) == 1:
        return possible_sorted[0]
    elif len(possible_sorted) == 0:
        print '*** Org not found in org list ***'
        return None
    else:
        while(True):
            for org in possible_sorted:
                count += 1
                print count, org.name
            index = int(raw_input('Which org to use? '))
            if index <= len(possible_sorted) and index > 0:
                return possible_sorted[index-1]
            else:
                print '*** Number not found in possible org list ***'
                return None

def choose_path(org):
    #Example URL to create:
    #https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2637&pathid=7971&startDate=1411171597714&endDate=1411258031465&loadSeqTz=false - 1411258634
    """
    Collect user input partial path name, look at paths in this org, list paths, allow user to choose path, open path in browser
    @param org:
    @return: none
    """
    partial_name = raw_input('Partial path name? ').rstrip()
    end_sec = int(time.time())
    start_sec = end_sec - (24 * 60 * 60) # one day
    end = end_sec * 1000 # milliseconds
    start = start_sec * 1000 # milliseconds
    # filter = {'name':'*' + partial_name.lower() + '*'}
    path_list = org.get_path_set()
    paths_unsorted = []
    for path in path_list:
        if partial_name.lower() in path.pathName.lower():
            paths_unsorted.append(path)
    paths = sorted(paths_unsorted, key=lambda k: k.pathName)
    if len(paths) == 0:
        print 'No matching path found'
    elif len(paths) > 1:
        pathNum = 0
        for path in paths:
            pathNum += 1
            print str(pathNum) + '\t' + path.pathName
        pathChoice = True
        while pathChoice:
            pathCh = raw_input('Open which path? ').rstrip()
            if pathCh == 'q' or pathCh == 'Q' or pathCh == '' or pathCh == '0':
                break
            try:
                pathCh = int(pathCh)
            except:
                break

            if pathCh <= pathNum and pathCh > 0:
                url = pv.create_url_path(pvc, paths[pathCh-1], start, end)
                pv.open_web(url)
                # pv.open_web(pv.create_url_path(pvc, paths3[pathCh-1], start, end))
    else:
        pv.open_web(pv.create_url_path(pvc, paths[0], start, end))

def choose_path_by_ip(org):
    #Query user for IP address
    ip_needed = raw_input('Target IP address? ').rstrip()
    is_subnet = '/' in ip_needed
    if is_subnet:
        subnet = ip.Ip4Subnet(ip_needed, 'Subnet')
        #Find all paths in the org
        paths = pv.get_paths(creds, org)
    else:
        paths = pv.get_paths(creds, org, target=ip_needed)
    paths2 = []
    #Search thru looking for this IP address or subnet range
    for path in paths:
        if path.ip == '10.252.0.30':
            asdf = 1
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

def path_param_exceeds(org, creds, measure, threshold):
    '''
    Find paths where the specified parameter (initially loss) exceeds the given threshold during the last hour
    @param org:
    @param measure:
    @param threshold:
    @return:
    '''
    #TODO should be able to use existing path_list?
    all_paths = pv.get_paths(creds, org)
    paths = []
    for path in all_paths:
        measures = pv.get_path_param(creds, path, measure)
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

# def is_csv(filList):
#     newList = []
#     for handle in filList:
#         if (handle.lower()[-4:] == '.csv'):
#             newList.append(handle)
#     return newList

def choose_csv():
    """
    Show csv files in local directory, user chooses by number
    @return: filename as text string
    """
    # choice = raw_input('\nName of input file? ').strip()
    csv_list = glob.glob("./*.csv")
    while True:
        if len(csv_list) > 0:
            file_num = 0
            for csv_file_name in csv_list:
                file_num += 1
                print str(file_num) + '\t' + csv_file_name
            file_choice = True
            while file_choice:
                file_choice = raw_input('Open which file? ').rstrip()
                if file_choice == 'q' or file_choice == 'Q' or file_choice == '' or file_choice == '0':
                    break
                try:
                    file_choice = int(file_choice)
                except:
                    break

                if file_choice <= file_num and file_choice > 0:
                    return csv_list[file_num-1]

def create_paths(org):
    """
    Choose local csv file that defines new paths, create paths
    @return: nada
    """
    in_fields = [
        'sourceAppliance',
        'target',
        'applianceInterface',
        'groupName',
        'asymmetric',
        'pathName',
        'inboundName',
        'outboundName',
        'networkType',
        'qosName',
        'alertProfileId'
        ]
    '''
    use choose_csv() to have user pick a local file
    '''
    path_file_name = choose_csv()
    '''
        open file and import csv lines, change org name to org ID, use dict to create a path
    '''
    path_file = open(path_file_name, 'rb')
    path_csv = csv.reader(path_file, delimiter=',', quotechar='"')
    try:
        ''' read in a line from CSV file '''
        for row in path_csv:
            ''' create dict using names from in_fields and values from row '''
            path_dict = {}
            item_num = 0
            if len(in_fields) <> len(row):
                raise ValueError ('input field does not match in_fields length')
            elif row[0] <> 'Src':
                for item in row:
                    path_dict[in_fields[item_num]] = item
                    item_num += 1
                ''' find current org '''
                # org = pv.find_org(path_dict['orgId'], org_set)
                #TODO add org to CSV as a check?
                #TODO check to see if org in file matches current org, if not, offer to change
                #TODO if org not available to this user, print appropriate error message and quit
                ''' fix up cells '''
                if org:
                    ''' add orgId'''
                    path_dict['orgId'] = org.id
                else:
                    raise ValueError('No matching org found for ' + row)
                if path_dict['asymmetric'] == 'Single':
                    ''' change symmetric to true or false '''
                    path_dict['asymmetric'] = 'true'
                else:
                    path_dict['asymmetric'] = 'false'
                ''' find identified alert profile '''
                alert_set = org.get_alert_set()
                profile = alert_set.find_alert(path_dict['alertProfileId'])
                ''' change alertProfileId from name to id value'''
                path_dict['alertProfileId'] = profile.id
                org.create_path(path_dict)
    except:
        raise

"""
----------------------------------------------------------------------
                   MAIN
----------------------------------------------------------------------
"""

options = {
    '0': ['Exit'],
    '1': ['Choose an organization'],
    '2': ['Display a path in current org'],
    '3': ['Open diagnostics from deep link'],
    '4': ['Display path by IP address or CIDR subnet'],
    '5': ['Paths with loss in the last hour (slow)'],
    '6': ['Create Paths'],
    # '7': ['Check org ids']
}

txt_files = glob.glob("./*.txt")
if ".\\user.txt" in txt_files:
    user_file = open ("./user.txt", 'rb')
    for row in user_file:
        id, value = row.split(": ")
        value = value.rstrip()
        if id == 'username':
            user = value
        elif id == 'password':
            password = value
        elif id == 'pvc':
            pvc = value
else:
    pvc = raw_input("PathView Cloud Address? (inc. https://... ")
    user = raw_input("PathView user name? ").rstrip()
    password = raw_input("PathView password? ").rstrip()

def printem(the_string):
    print the_string



creds = pv.Credentials(pvc, user, password)

global org_set
org_set = pv.Org_list(creds).org_list

print
org = None
while org == None:
    org = choose_org()
org.open_org()
org.init_path_set()
while True:
    menu(options, org)
    choice = raw_input('\nChoice? ').strip()
    if choice == '0':
        break
    if choice == '1':
        org = choose_org()
        # if org:
        #     alert_set = org.get_alert_set()
    if choice == '2':
        choose_path(org)
    if choice == '3':
        pv.open_diag_this_path_view(org)
    if choice == '4':
        org.choose_path_by_ip()
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
        create_paths(org)
