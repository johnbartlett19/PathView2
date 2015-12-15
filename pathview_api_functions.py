import requests, datetime, webbrowser, sys
import windows as w
import urllib3
import certifi

http = urllib3.PoolManager(
    cert_reqs = 'CERT_REQUIRED', #Force certificate check
    ca_certs=certifi.where(),  # Path to the Certifi bundle
)
2

'''
API Documentation here:
https://polycom.pathviewcloud.com/pvc-data/swagger/#
'''

# These definitions point at a cloud and a user/password that allows access to that cloud
# pvc = 'https://polycom.pathviewcloud.com'
#user = 'test_api_access' # this one for Polycom IT only
#password = 'M8bxA1$WZ1*b'

class Path():
    """
    This class represents a PathView path.  Upon creation pass in a dictionary that includes:
     pathName:'Path Name'
     target:'Target IP address'
     pathId: 'Path ID value'
     organization: 'Org to which the path belongs'
    """
    def __init__(self, path_dict):
        self.dict = path_dict
        self.pathName = path_dict['pathName']
        self.ip = path_dict['target']
        self.id = path_dict['id']
        self.orgId = path_dict['orgId']
    def __repr__(self):
        return self.pathName

class Org():
    """
    Build class representing each Org to cross reference ID and name as needed
    """
    def __init__(self, json_array):
        self.dict = json_array
        self.name = self.dict['displayName']
        self.id = self.dict['id']
    def __repr__(self):
        return self.name

class Org_list():
    def __init__(self, pvc, user, password):
        try:
            org_raw = requests.get(pvc + '/pvc-data/v2/organization', auth=(user,password)).json()
            self.org_list = []
            for org_dict in org_raw:
                self.org_list.append(Org(org_dict))
        except requests.exceptions.Timeout:
            # Maybe set up for a retry, or continue in a retry loop
            print 'Network timeout, what is going on?'
            sys.exit(1)
        except requests.exceptions.TooManyRedirects:
            # Tell the user their URL was bad and try a different one
            print'Bad URL, try another?'
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            # catastrophic error. bail.
            print e
            sys.exit(1)

class Alert():
    """
    Build class representing each Org to cross reference ID and name as needed
    """
    def __init__(self, json_array):
        self.dict = json_array
        self.name = self.dict['name']
        self.id = self.dict['id']
    def __repr__(self):
        return self.name

class Alert_list():
    def __init__(self, org, pvc, user, password):
        org_info = {'orgId':org.id}
        try:
            alert_raw = requests.get(pvc + '/pvc-data/v2/alertProfile', params=org_info, auth=(user,password)).json()
            self.alert_list = []
            for alert_dict in alert_raw:
                self.alert_list.append(Alert(alert_dict))
        except requests.exceptions.Timeout:
            # Maybe set up for a retry, or continue in a retry loop
            print 'Network timeout, what is going on?'
            sys.exit(1)
        except requests.exceptions.TooManyRedirects:
            # Tell the user their URL was bad and try a different one
            print'Bad URL, try another?'
            sys.exit(1)
        except requests.exceptions.RequestException as e:
            # catastrophic error. bail.
            print e
            sys.exit(1)

def requests_logging():
    import httplib, logging
    httplib.HTTPConnection.debuglevel = 1
    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True

def get_path(pvc, user, password, pathid, org_set):
    """
    fetch path info for one path based on pathid
    @param pvc: url for cloud (e.g. 'https://polycom.pathviewcloud.com'
    @param user: username for cloud credentials
    @param password: password for cloud credentials
    @param pathid: numerical path ID for requested path
    @return: path object, json format (Dict)
    """
    try:
        return Path(requests.get(pvc + '/pvc-ws/v1/paths/' + str(pathid), auth=(user,password)).json(), org_set, user, password)
    except requests.exceptions.Timeout:
        # Maybe set up for a retry, or continue in a retry loop
        print 'Network timeout, what is going on?'
        sys.exit(1)
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        print'Bad URL, try another?'
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        print e
        sys.exit(1)

def get_path_param(pvc, user, password, path, measure):
    return requests.get(pvc + '/pvc-ws/v1/paths/' + str(path.id) + '/data/' + measure, auth=(user, password)).json()

def get_paths(pvc, user, password, org, target=None, filters=None):
    """
    get list of paths for specific org.
    @param user: username for cloud credentials
    @param password: password for cloud credentials
    @param org_name: organization within cloud to search by org name
    @param org_id: organization within cloud to search by org id
    @filters: dict of filters to apply to the search
    @return: list of paths (class Path)
    """
    payload = filters
    payload['orgId'] = org.id
    if target != None:
        payload['target'] = target
    page = 1
    paths = []
    while(1):
        payload['page'] = page
        path_page = requests.get(pvc + "/pvc-data/v2/path", params=payload, auth=(user, password), verify=False).json()
        paths += path_page
        if len(path_page) < 100:
            break
        page += 1
    path_set = []
    for path in paths:
        path_set.append(Path(path))
    return path_set

def get_org_id(org_name, org_set):
    return org_set.org_codes[org_name]

def open_org(org, pvc):
    base = pvc + '/pvc/welcome.html'
    args = {}
    args['st'] = str(org.id)
    url = form_url(base, args)
    open_web(url)

def form_url(base, args):
    """
    create a path URL to open a path view in browser
    args may include start and end times
    args in dictionary format
    @param base: base URL info including pathview cloud URL and 'path'
    @param args: dictionary of arguments to add to URL
    @return: string - URL fully formed
    """
    arg_str = ''
    for arg in args:
        arg_str = arg_str + '&' + arg + '=' + str(args[arg])
    arg_str = arg_str[1:]
    if len(arg_str) > 0:
        url = base + '?' + arg_str
    else:
        url = base
    return url

def create_url_diag(pvc, orgId, diag_id, tab=0):
    url = pvc + '/pvc/emberview/testdetail/test/' + str(diag_id) + '/data'
    # args = {}
    # args['st'] = str(orgId)
    # args['testid'] = str(diag_id)
    # args['activeTabTest'] = str(tab)
    # url = form_url(base, args)
    # https://polycom.pathviewcloud.com/pvc/emberview/testdetail/test/3576135/summary
    # https://polycom.pathviewcloud.com/pvc/emberview/testdetail/test/3576135/data

    return url

def create_url_path(pvc, path, start=None, end=None):
    """
    create a deep link url that will open a page for the specific start/end time window
    https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2590&pathid=10891&startDate=1448480802328&endDate=1449863659586&loadSeqTz=false

    @param path: path object (Dict)
    @param start: start time in unix seconds
    @param end: end time in unix seconds
    @return: url string
    """
    url_base = pvc +  '/pvc/pathdetail.html'
    newPathDict = {}
    if start != None:
        newPathDict['startDate'] = start
    if end != None:
        newPathDict['endDate'] = end
    newPathDict['st'] = path.orgId
    newPathDict['pathid'] = str(path.id)
    newPathDict['loadSeqTz']= 'false'
    url = form_url(url_base, newPathDict)
    return url

def simple_url_path(pvc, path):
    """
    create a simple url that will open a page for a specific path
    @param path: path object (Dict)
    @param start: start time in unix seconds
    @param end: end time in unix seconds
    @return: url string
    """
    url_base = pvc +  '/pvc/pathdetail.html'
    newPathDict = {}
    newPathDict['pathid'] = path['pathId']
    newPathDict['loadSeqTz']= 'false'
    url = form_url(url_base, newPathDict)
    return url


def unix_time(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return int(delta.total_seconds()* 1000)

def find_diags(pvc, user, password, path_id, start, end):
    diags = requests.get(pvc + "/pvc-data/v2/diagnostic", auth=(user, password), params={'pathId':path_id,'from':start,'to':end})
    # https://polycom.pathviewcloud.com/pvc/emberview/testdetail/test/3576658/summary
    return diags.json()

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

def find_path_partial_name(partial, pvc, user, password, org=None):
    paths = get_paths(pvc, user, password, org_name=org)
    for path in paths:
        if partial in path.pathName:
            open_web(create_url_path(pvc,path))

def open_diag_this_path_view(pvc, user, password):
    def open_diags(deep_link):
        linkDict = parse_deep_link(deep_link)
        diags = find_diags(pvc, user, password, linkDict['pathid'], int(linkDict['startDate'])/1000, int(linkDict['endDate'])/1000)
        # find all diags in this range
        for diag in diags:
            url = create_url_diag(pvc, linkDict['st'], diag['testId'],tab=1)
            open_web(url)
    w.input_window('Deep Link:', open_diags)
    # deep_link = raw_input('Deep link reference: ')

def paths_to_file(paths, filename):
    out_file = open(filename, 'wb')

    for path in paths:
        if 'qosName' in path.dict:
            qos = path.dict['qosName']
        else:
            qos = 'None'
        out_file.write(path.pathName + '\t' + path.ip + '\t' + path.dict['instrumentation'] + '\t' + path.dict['networkType'] + '\t' + path.dict['sourceAppliance'] + '\t' + qos + '\n')
    out_file.close()

def create_path(path_dict, pvc, user, password):
    """
    Use path object information to initiate path on pathview cloud
    @param path: path object defining the path
    @return:True for success, False for failure
    """
    c_path_resp = requests.post(pvc + "/pvc-data/v2/path", json=path_dict, auth=(user, password))
    return c_path_resp

def find_org(org_name, org_set):
    """
    Given name of org, search org set for org with name and return org
    @param org_name: text string org name
    @param org_set:
    @return:
    """
    for org in org_set:
        if org.name == org_name:
            return org
    return False

def find_alert(profile_name, alert_set):
    """
    Search through alert_set, find alert that has name profile_name and return it
    @param profile_name: name of alert we want to find
    @param alert_set: list of Alerts
    @return: found Alert or False
    """
    for alert in alert_set:
        if alert.name == profile_name:
            return alert
    return False
