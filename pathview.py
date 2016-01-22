#TODO Add ability to find top ten paths with 1-day or 7-day violations
#TODO Test pulling orgs as other than super user
#TODO Add test for appliances that are not connected
#TODO Find paths with specific alert or not specific alert (e.g. not using Polycom Video or using 'Connectivity') (easy!)
#TODO Check routine that pulls data from multiple paths, see note below
'''
Hi John,
I wanted to chime in to let you know that when retrieving data from multiple paths and specifying a to and from time you're going to want to put the time in milliseconds. I know this is not consistent with pulling data from a single path and our dev team is looking to correct that.
Let us know if you have any other questions.
Shaun
'''

import pathview_api_functions as pv, ip_address_functions as ip, time, csv
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


def open_diag():
    raise ValueError('Not defined')


def list_and_choose_path(description, path_list):
    """
    Takes a list of paths and a description.  Prints out description, then lists paths with an index so user
    can choose which path to display.  If user chooses a path, opens the web page associated with that path.
    Stays in this routine until user chooses '0', q etc. or provides no answer, then exits back to calling routine
    @param description: Text string to be printed before listing paths
    @param path_list: list of path objects [path1, path2, path3 ..]
    @return:
    """
    pathNum = 0
    print
    print description
    print
    for path in path_list:
        pathNum += 1
        print str(pathNum) + '\t' + path.pathName
    while True:
        path_choice = raw_input('Open a path? ').rstrip()
        if path_choice.lower() in ['q', '', '0', 'quit']:
            break
        try:
            path_choice = int(path_choice)
        except:
            break

        if path_choice <= pathNum and path_choice > 0:
            url = pv.create_url_path(pvc, path_list[path_choice-1])
            pv.open_web(url)

def menu(options, org):
    print '\n'
    print 'Org:', org
    for key in sorted(options):
        print key + ':', options[key][0]


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
                    return csv_list[file_choice-1]


def create_paths(org):
    """
    Choose local csv file that defines new paths, create paths
    @return: nada
    """
    in_fields = [
        'org',
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
                raise ValueError ('Length of file row does not match expected fields length')
            elif row[0] <> 'Org':
                for item in row:
                    path_dict[in_fields[item_num]] = item
                    item_num += 1
                ''' verify org is current org '''
                if path_dict['org'] != org.name:
                    raise ValueError("Org name in CSV file does not match current org.  CSV: " + path_dict['org'] + ' Current: ' + org.name)
                ''' fix up cells '''
                if org:
                    ''' add orgId'''
                    path_dict['orgId'] = org.id
                else:
                    raise ValueError('No matching org found for ' + row)
                if path_dict['asymmetric'] == 'Single':
                    ''' change asymmetric to true or false '''
                    path_dict['asymmetric'] = 'false'
                elif path_dict['asymmetric'] == 'Double':
                    path_dict['asymmetric'] = 'true'
                else:
                    raise ValueError ('Single/Double field value not recognized')
                ''' find identified alert profile '''
                alert_set = org.get_alert_set()
                profile = alert_set.find_alert(path_dict['alertProfileId'])
                ''' change alertProfileId from name to id value'''
                path_dict['alertProfileId'] = profile.id
                org.create_path(path_dict)
    except ValueError as e:
        print e
    except:
        raise

def find_qos_violations(org):
    """
    Check all paths in this org, find those that have a QoS change, print list of paths, provide option
      to write list out in csv format to a file
    @param org:
    @return:
    """
    mid_path_query = raw_input('Find paths with mid-path violations? ').rstrip()
    if mid_path_query.lower() in ['y', 'Y', 'yes', 'Yes', 'YES']:
        qos_path_list, path_no_diag = org.find_paths_qos(by_hop=True)
    else:
        qos_path_list, path_no_diag = org.find_paths_qos(by_hop=False)

    print 'Found ' + str(len(qos_path_list)) + ' paths with QoS violations'
    print 'Found ' + str(len(path_no_diag)) + ' paths with no available diagnostic'

    while True:
        print
        print_query = raw_input('Show qos or show no_diag [qos | diag]? ')
        if print_query.lower() in ['qos', 'y', 'yes']:
            list_and_choose_path('QoS Violation List', qos_path_list)
        elif print_query.lower() in ['d', 'diag']:
            list_and_choose_path('Paths with no diagnostic found', path_no_diag)
        else:
            break

'''
----------------------------------------------------------------------
                   MAIN
----------------------------------------------------------------------
'''

options = {
    '0': ['Exit'],
    '1': ['Choose an organization'],
    '2': ['Display a path in current org'],
    '3': ['Open diagnostics from deep link'],
    '4': ['Display path by IP address or CIDR subnet'],
    '5': ['Paths with loss in the last hour (slow)'],
    '6': ['Create Paths'],
    '7': ['Find paths with QoS Changes']
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
    pvc = raw_input("PathView Cloud Address? (inc. https://... ").rstrip()
    user = raw_input("PathView user name? ").rstrip()
    password = raw_input("PathView password? ").rstrip()

def printem(the_string):
    print the_string


def change_org():
    org = choose_org()
    org.open_org()
    org.init_path_set()
    return org

creds = pv.Credentials(pvc, user, password)

global org_set
org_set = pv.Org_list(creds).org_list

print
org = change_org()
while True:
    menu(options, org)
    choice = raw_input('\nChoice? ').strip()
    if choice == '0':
        break
    if choice == '1':
        org = change_org()
        # if org:
        #     alert_set = org.get_alert_set()
    if choice == '2':
        choose_path(org)
    if choice == '3':
        org.open_diag_this_path_view()
    if choice == '4':
        org.choose_path_by_ip()
    if choice == '5':
        # path_param_exceeds(self, measure, threshold, start=int(time.time())-60*60, end=int(time.time())):
        measure = 'dataLoss'
        threshold = 0.01
        paths = org.path_param_exceeds2(measure, threshold)
        pathNum = 0
        print
        for path in paths:
            pathNum += 1
            print str(pathNum) + '\t' + path.pathName + '\t' + path.target_ip
        print
        pathChoice = True
        while pathChoice:
            pathChoice = raw_input('Open which path? ').rstrip()
            try:
                pathCh = int(pathChoice)
                if pathCh <= pathNum:
                    paths[pathCh-1].open_web()
            except:
                if pathNum == 'q' or pathNum == 'Q' or pathNum == '' or pathNum == '0':
                    break
    if choice == '6':
        create_paths(org)
    if choice == '7':
        find_qos_violations(org)

# https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2590&pathid=10891&startDate=1451251082067&endDate=1451257513914&loadSeqTz=false