#TODO Add ability to find top ten paths with 1-day or 7-day violations.  No access to violations in API
#TODO Check routine that pulls data from multiple paths, see note below
#TODO Pull performance data from multiple paths to reduce time?  10 paths at a time perhaps?  See note below about specifying time windows
#TODO Fix show paths with Alert to list paths and allow path choice for display.  This should use a common subroutine?
#TODO When listing paths for QoS check, show count (e.g. path 1 of 117) to show progress
#TODO Does qos analysis look at both directions of bi-directional paths?
'''
starting the script in the Idle shell:
setx PATH "%PATH%;C\Python27"
must be run as administrator
can start in idle window but need to call with python otherwise modules can't be found.
try:  python -m idle.py -r pathview.py
'''

import pathview_api_functions as pv, csv
import glob

def choose_org():
    find_org = input('Fragment of organization name? ').lower().rstrip()
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
        print('*** Org not found in org list ***')
        return None
    else:
        while(True):
            for org in possible_sorted:
                count += 1
                print(count, org.name)
            index = input('Which org to use? ')
            if index in ['0','','exit']:
                return None
            try:
                index = int(index)
                if index <= len(possible_sorted) and index > 0:
                    return possible_sorted[index-1]
                else:
                    print('*** Number not found in possible org list ***')
            except:
                pass

def choose_path(org):
    #Example URL to create:
    #https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2637&pathid=7971&startDate=1411171597714&endDate=1411258031465&loadSeqTz=false - 1411258634
    """
    Collect user input partial path name, look at paths in this org, list paths, allow user to choose path, open path in browser
    @param org:
    @return: none
    """
    partial_name = input('Partial path name? ').rstrip()
    # filter = {'name':'*' + partial_name.lower() + '*'}
    path_list = org.get_path_set()
    paths_unsorted = []
    for path in path_list:
        if partial_name.lower() in path.pathName.lower():
            paths_unsorted.append(path)
    pv.list_and_choose_path('Paths with partial name ' + partial_name, paths_unsorted, window_param=(24,'hour'))


def menu(options, org):
    print('\n')
    print('Org:', org)
    print('Path count: ', len(org.path_set))
    list1 = options.keys()
    list1 = [int(x) for x in list1]
    list1.sort()
    for item in list1:
        print(str(item) + ':', options[str(item)][0])


def choose_csv():
    """
    Show csv files in local directory, user chooses by number
    @return: filename as text string
    """
    # choice = input('\nName of input file? ').strip()
    csv_list = glob.glob("./*.csv")
    while True:
        if len(csv_list) > 0:
            file_num = 0
            for csv_file_name in csv_list:
                file_num += 1
                print(str(file_num) + '\t' + csv_file_name)
            file_choice = True
            while file_choice:
                file_choice = input('Open which file? ').rstrip()
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
    path_file = pv.reencode(open(path_file_name, 'rb'))
    '''
    def reencode(file):
    for line in file:
        yield line.decode('windows-1250').encode('utf-8')

    csv_reader = csv.reader(reencode(open(filepath)), delimiter=";",quotechar='"')

        # .decode(locale.getpreferredencoding())
    # open('f1').read().decode('utf8')
    '''
    path_csv = csv.reader(path_file, dialect='excel', delimiter=',', quotechar='"')
    # path_csv = csv.reader()
    row_count = 0
    try:
        ''' read in a line from CSV file '''
        for row in path_csv:
            row_count += 1
            ''' create dict using names from in_fields and values from row '''
            if row[0] == '':
                print('Input file row ' + str(row_count) + ' has no value in Org field, skipping')
                continue
            path_dict = {}
            item_num = 0
            if len(in_fields) != len(row):
                raise ValueError ('Length of file row does not match expected fields length')
            elif row[0] != 'Org':
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
                profile = alert_set.find_by_name(path_dict['alertProfileId'])
                if profile == False:
                    raise ValueError('\n*** Unable to find value: ' + path_dict['alertProfileId'] + 'in Alert Profile list for this Org***')
                ''' change alertProfileId from name to id value'''
                path_dict['alertProfileId'] = profile.id
                org.create_path(path_dict)
    except ValueError as e:
        print(e)
    except:
        raise

def find_qos_violations(org):
    """
    Check all paths in this org, find those that have a QoS change, print list of paths, provide option
      to write list out in csv format to a file
    @param org:
    @return:
    """
    #TODO - don't count intermediate hops where QoS is listed as '-'
    qos_path_list, path_no_diag = org.find_paths_qos()
    print('Found ' + str(len(qos_path_list)) + ' paths with QoS violations')
    print('Found ' + str(len(path_no_diag)) + ' paths with no available diagnostic')
    while True:
        print()
        print_query = input('Show qos or show no_diag [qos | diag]? ').rstrip()
        if print_query.lower() in ['qos', 'y', 'yes']:
            last_hop = input('Include paths with QoS violation on last hop only? ').rstrip()
            if last_hop.lower() in ['y', 'yes']:
                pv.list_and_choose_path('QoS Violation List including last hop', qos_path_list, window_param=(1,'day'))
            else:
                qos_filtered_path_list = remove_last_hop_only(qos_path_list)
                pv.list_and_choose_path('QoS Violation List not including last hop', qos_filtered_path_list, window_param=(1,'day'))
        elif print_query.lower() in ['d', 'diag']:
            pv.list_and_choose_path('Paths with no diagnostic found', path_no_diag, window_param=(30, 'day'))
        else:
            break

def remove_last_hop_only(qos_path_list):
    path_list = []
    for path in qos_path_list:
        if path.qos_mid_change:
            path_list.append(path)
    return path_list

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
    '7': ['Find paths with QoS Changes'],
    '8': ['Show status of appliances'],
    '9': ['Show paths using a specific Alert Profile'],
    '10': ['Show paths belonging to a specific Group']
}


txt_files = glob.glob("./*.txt")
if ".\\user.txt" in txt_files:
    user_file = open ("./user.txt", 'r')
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
    pvc = input("PathView Cloud Address? (inc. https://... ").rstrip()
    user = input("PathView user name? ").rstrip()
    password = input("PathView password? ").rstrip()


def change_org():
    org = choose_org()
    if org:
        org.open_org()
        org.init_path_set()
    return org

def paths_by_alert(org):
    all_paths = org.get_path_set()
    alerts = org.get_alert_set()
    print('Paths in this org are using the following alerts')
    print('Choose an alert to get a list of paths using that alert')
    alert_dict = {}
    for path in all_paths:
        if path.alertProfileId in alert_dict:
            alert_dict[path.alertProfileId][0] += 1
        else:
            alert_dict[path.alertProfileId] = [1]
    for profId in alert_dict:
        alert_dict[profId].append(alerts.find_by_id(profId))
    while True:
        fmt = '\n{0:5s}{1:37s}{2:10s}'
        print(fmt.format('   #', ' Profile', 'Path Count'))
        fmt = '{0:4d}  {1:37s}{2:3d}'
        item_count = 0
        alert_list = []
        for profId in alert_dict:
            item_count += 1
            print(fmt.format(item_count, alert_dict[profId][1].name, alert_dict[profId][0]))
            alert_list.append(profId)
        print()
        choice = input('Choose alert to list paths, 0 to exit: ').rstrip()
        if choice in ['0', '', 'n']:
            return
        elif int(choice) <= len(alert_list):
            id = alert_list[int(choice)-1]
            message = '\nPaths using Alert ' + alert_dict[id][1].name + ':'
            path_list = []
            for path in all_paths:
                if path.alertProfileId == id:
                    path_list.append(path)
            start = 1
            pv.list_and_choose_path(message, path_list, window_param=(1, 'day'))

def paths_by_group(org):
    all_paths = org.get_path_set()
    groups = org.get_groups()
    print('Paths in this org are using the following groups')
    print('Choose a group to get a list of paths using that group')
    group_dict = {}
    for path in all_paths:
        if path.group in group_dict:
            group_dict[path.group] = (group_dict[path.group][0] + 1, group_dict[path.group][1] + [path])
        else:
            group_dict[path.group] = (1,[path])
    while True:
        fmt = '\n{0:5s}{1:37s}{2:10s}'
        print(fmt.format('   #', ' Group', 'Path Count'))
        fmt = '{0:4d}  {1:37s}{2:3d}'
        item_count = 0
        group_keys = list(group_dict.keys())
        group_keys.sort()
        for group in group_keys:
            item_count += 1
            print(fmt.format(item_count, group, group_dict[group][0]))
        print()
        choice = input('Choose group to list paths, 0 to exit: ').rstrip()
        if choice in ['0', '', 'n']:
            return
        elif int(choice) <= len(group_keys):
            id = int(choice)-1
            message = '\nPaths in group ' + group_keys[id] + ':'
            pv.list_and_choose_path(message, group_dict[group_keys[id]][1], window_param=(1, 'day'))


def find_appliance_connection_status(org):
    appl_list = org.get_appliances()
    fmt = '{0:30s}{1:10s}'
    print(fmt.format('Appliance', 'Status'))
    for appl in appl_list:
        print(fmt.format(appl.name, appl.conn_stat))

def find_paths_by_loss(org):
    # path_param_exceeds(self, measure, threshold, start=int(time.time())-60*60, end=int(time.time())):
        # TODO convert this to use the standard listing procedure if possible
    measure = 'dataLoss'
    threshold = 0.01 # 1% loss
    paths = org.path_param_exceeds2(measure, threshold)
    pv.list_and_choose_path('Paths with Packet Loss', paths, (1, 'hour'))
'''
-------------------------------------------------------------------------------------------------------------------------------------------
  MAIN
-------------------------------------------------------------------------------------------------------------------------------------------
'''

creds = pv.Credentials(pvc, user, password)

global org_set
org_set = pv.Org_list(creds).org_list

print()
org = None
while not org:
    org = change_org()
    if not org:
        print('*** No org with that name found, please select another ***')
while True:
    menu(options, org)
    choice = input('\nChoice? ').strip()
    if choice == '0':
        break
    if choice == '1':
        org = change_org()
    if choice == '2':
        choose_path(org)
    if choice == '3':
        org.open_diag_this_path_view()
    if choice == '4':
        org.choose_path_by_ip()
    if choice == '5':
        find_paths_by_loss(org)
    if choice == '6':
        create_paths(org)
    if choice == '7':
        find_qos_violations(org)
    if choice == '8':
        find_appliance_connection_status(org)
    if choice == '9':
        paths_by_alert(org)
    if choice == '10':
        paths_by_group(org)
