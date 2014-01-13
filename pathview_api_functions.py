import requests, datetime, webbrowser
from ip_address import *
#TODO build app to search for paths based on portion of path name, provide path ID and names in list
#TODO build function to open diags that occurred in given time window
pvc = 'https://polycom.pathviewcloud.com'
#user = 'test_api_access' # this one for Polycom IT only
#password = 'M8bxA1$WZ1*b'
user = 'Polycom_api'   # This one for all accounts
password = 'johnbartlett12'

def get_all_paths(pvc, user, password):
    """
    fetch all path info for cloud pvc
    @param pvc: url for cloud (e.g. 'https://polycom.pathviewcloud.com'
    @param user: username for cloud credentials
    @param password: password for cloud credentials
    @return: list of path objects, one for each path, json format (list of Dicts)
    """
    #payload = {'Accept': 'application/json'}
    paths = requests.get(pvc + "/pvc-ws/v1/paths", auth=(user, password))
    return paths.json()

def get_one_path(pvc, user, password, pathid):
    """
    fetch path info for one path based on pathid
    @param pvc: url for cloud (e.g. 'https://polycom.pathviewcloud.com'
    @param user: username for cloud credentials
    @param password: password for cloud credentials
    @param pathid: numerical path ID for requested path
    @return: path object, json format (Dict)
    """
    payload = {'Accept': 'application/json'}
    pvcquery = requests.get(pvc + '/pvc-ws/v1/paths/' + str(pathid), auth=(user, password))
    return [pvcquery.json()]

def get_paths_org(pvc, user, password, org):
    """
    get list of paths for specific org
    @param pvc: url for cloud (e.g. 'https://polycom.pathviewcloud.com'
    @param user: username for cloud credentials
    @param password: password for cloud credentials
    @param org: organization within cloud to search
    @return: list of path objects, json format
    """
    #paths = get_all_paths(pvc, user, password)
    paths = requests.get(pvc + "/pvc-ws/v1/paths", auth=(user, password), params = {'organization':org})
    return paths.json()

def paths_by_target_ip(pvc, user, password, target):
    """
    find list of paths with common IP target
    @param pvc:
    @param user:
    @param password:
    @param target:
    @return:
    """
    #TODO expand this to take wild cards
    paths = get_all_paths(pvc, user, password)
    retList = []
    for path in paths:
        if path['target'] == target:
            retList.append(path)
    return retList

def form_url(base, args):
    arg_str = ''
    for arg in args:
        arg_str = arg_str + '&' + arg
    arg_str = arg_str[1:]
    if len(arg_str) > 0:
        url = base + '?' + arg_str
    else:
        url = base
    return url

def form_url2(base, args):
    arg_str = ''
    for arg in args:
        arg_str = arg_str + '&' + arg + '=' + args[arg]
    arg_str = arg_str[1:]
    if len(arg_str) > 0:
        url = base + '?' + arg_str
    else:
        url = base
    return url

def unix_time(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return int(delta.total_seconds()* 1000)

def create_url_path(pvc, path, start, end):
    """
    create a deep link url that will open a page for the specific start/end time window
    @param path: path object (Dict)
    @param start: start time in unix seconds
    @param end: end time in unix seconds
    @return: url string
    """
    #'https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2153&pathid=4464&startDate=1388579369210&endDate=1388582973999&loadSeqTz=false'
    # This is the IT account
    #https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2153&pathid=7045&startDate=1389125191941&endDate=1389128801613&loadSeqTz=false
    #https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2153&pathid=7044&startDate=1389125194750&endDate=1389128830272&loadSeqTz=false
    #https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2153&pathid=7046&startDate=1389125194665&endDate=1389128843009&loadSeqTz=false
    #https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2153&pathid=8127&startDate=1389125254094&endDate=1389128857245&loadSeqTz=false
    ## This is the Experian account
    #https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=551&pathid=8471&startDate=1389125328719&endDate=1389128935911&loadSeqTz=false
    #https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=551&pathid=8278&startDate=1389125330036&endDate=1389128952220&loadSeqTz=false
    #https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=551&pathid=8461&startDate=1389125331309&endDate=1389128964802&loadSeqTz=false
    #https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=551&pathid=8353&startDate=1389125332568&endDate=1389128980819&loadSeqTz=false
    # TODO convert this to use form_url2, delete form_url
    url_base = pvc +  '/pvc/pathdetail.html'
    st = 'st=2153'  #don't know what this is
    pathid = 'pathid=' + str(path['pathId'])
    startDate = 'startDate='+str(start)
    endDate = 'endDate=' + str(end)
    loadSeq = 'loadSeqTz=false'
    arg_list = [st, pathid, startDate, endDate, loadSeq]
    url = form_url(url_base, arg_list)
    return url

def find_diags(pvc, user, password, path_id, start, end):
    diags = requests.get(pvc + "/pvc-ws/v1/diagnostics", auth=(user, password), params = {'pathId':path_id,'from':start,'to':end})
    return diags.json()

def create_url_diag(pvc, orgId, diag_id, tab=0):
    base = pvc + '/pvc/testdetail.html'
    args = {}
    args['st'] = str(orgId)
    args['testid'] = str(diag_id)
    args['activeTabTest'] = str(tab)
    url = form_url2(base, args)
    return url

# build this:
# https://polycom.pathviewcloud.com/pvc/testdetail.html?st=551&testid=1190951&activeTabTest=0
# https://polycom.pathviewcloud.com/pvc/testdetail.html?st=551&testid=1190951&activeTabTest=1

def open_web(url):
    new = 2 # open in a new tab, if possible
    webbrowser.open(url,new=new)

def parse_deep_link(deep_link):
    url, args = deep_link.split('?')
    arg_list = args.split('&')
    arg_dict = {}
    for arg in arg_list:
        name, value = arg.split('=')
        arg_dict[name] = value
    return  arg_dict

def get_start_end():
    deep_link = raw_input('Deep link: ')
    link_dict = parse_deep_link(deep_link)
    return (link_dict['startDate'],link_dict['endDate'])



#target = '10.250.7.10'
#target = '172.27.209.80'
#pathlist = paths_by_target_ip(pvc, user, password, target)

#print 'Total Length', len(pathlist)

#start_string = raw_input('Start time mm/dd/yyyy hh:mm (24hr): ')
#end_string = raw_input('End time mm/dd/yyyy hh:mm (24hr): ')
#format = '%m/%d/%Y %H:%M'
#start_dt = datetime.datetime.strptime(start_string, format)
#end_dt = datetime.datetime.strptime(end_string, format)

#start, end = get_start_end()
#for path in pathlist:
#    open_web(create_url_path(pvc, path, start, end))

#aa = create_url_path(pvc,pathlist[2],unix_time(start_dt), unix_time(end_dt))
#open_web(aa)
#print aa

#start, end = get_start_end()
def print_paths_for_org(org):
    aa = get_paths_org(pvc, user, password,'C-CALA-BTG')
    for path in aa:
        for key in path:
            print key, path[key]
    print 'Total paths = ', len(aa)

# https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=551&pathid=8471&startDate=1389201166226&endDate=1389215601545&loadSeqTz=false

#find all diagnostics for this path within this timeslot and open web pages for each on the details page
def open_diag_this_path_view():
    deep_link = raw_input('Deep link reference: ')
    linkDict = parse_deep_link(deep_link)
    diags = find_diags(pvc, user, password, linkDict['pathid'], int(linkDict['startDate'])/1000, int(linkDict['endDate'])/1000)
    # find all diags in this range
    for diag in diags:
        url = create_url_diag(pvc, linkDict['st'], diag['testId'],tab=1)
        #print url
        open_web(url)

