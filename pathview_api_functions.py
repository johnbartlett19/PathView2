import requests, datetime, webbrowser, sys, json
import windows as w
import ip_address_functions as ip
import urllib3, certifi, time

http = urllib3.PoolManager(
    cert_reqs = 'CERT_REQUIRED', #Force certificate check
    ca_certs=certifi.where(),  # Path to the Certifi bundle
)


'''
API Documentation here:
https://polycom.pathviewcloud.com/pvc-data/swagger/#
'''

#TODO - make alert list be a component of the org

class Credentials():
    def __init__(self, pvc, user, password):
        self.pvc = pvc
        self.user = user
        self.password = password
    def __repr__(self):
        return self.user


class Org():
    """
    Build class representing each Org to cross reference ID and name as needed
    """
    def __init__(self, json_array, creds):
        self.dict = json_array
        self.name = self.dict['displayName']
        self.id = self.dict['id']
        self.path_set = None
        self.creds = creds
        self.alert_set = None

    def __repr__(self):
        return self.name

    def init_path_set(self):
        """
        Pull info from this org on all paths and create a list of path objects self.path_set
        @return:
        """
        page_len = 999
        payload = {}
        payload['orgId'] = self.id
        page = 1
        paths = []
        while(1):
            payload['page'] = page
            payload['limit'] = page_len
            path_set = pathview_http('GET', 'pvc-data/v2/path', self.creds, fields=payload)
            path_page = json.loads(path_set.data)
            paths += path_page
            if len(path_page) < page_len:
                break
            page += 1
        self.path_set = []
        for path in paths:
            self.path_set.append(Path(self, path))

    def create_path(self, path_dict):
        """
        Use path object information to initiate path on pathview cloud
        @param path: path object defining the path
        @return:True for success, False for failure
        """
        headers = urllib3.util.make_headers(basic_auth=self.creds.user + ':' + self.creds.password)
        url = self.creds.pvc + '/pvc-data/v2/path'
        headers['Content-Type'] = 'application/json'
        c_path_http =  http.request('POST', url, headers=headers, body=json.dumps(path_dict))
        if c_path_http.status > 399:
            http_data = json.loads(c_path_http.data)
            print path_dict['pathName'] + ': ' + http_data['messages'][0]
            return False
        # elif c_path_data.reason == 'Created':
        #     print path_dict['pathName'] + ': ' + c_path_http.reason
        else:
            print path_dict['pathName'] + ': Created'
            c_path_data = json.loads(c_path_http.data)
            c_path = Path(self, c_path_data)
            self.path_set.append(c_path)
            return (c_path)

    def get_path_set(self):
        """
        Get the path set from this org.  If the path set has not been created, create it first
        @return:
        """
        if self.path_set == None:
            self.init_path_set()
        return self.path_set

    def path_by_id(self, path_id):
        """
        Find path in path set with this path_id
        @param path_id:
        @return: path or False
        """
        path_set = self.get_path_set()
        for path in path_set:
            if path.id == int(path_id):
                return path
        return False

    def get_alert_set(self):
        """
        Return this org's alert set.  If alert set info has not been pulled, do it now
        @return:
        """
        if self.alert_set == None:
            self.alert_set = Alert_list(self)
        return self.alert_set

    def open_org(self):
        base = self.creds.pvc + '/pvc/welcome.html'
        args = {}
        args['st'] = str(self.id)
        url = form_url(base, args)
        open_web(url)

    def open_diag_this_path_view(self, deep_link):
        """
        https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2590&pathid=11866&startDate=1451050162122&endDate=1451053787270&loadSeqTz=false
        Using a deep link as input, find the diagnostic events in the viewed time window of this path
        @param creds:
        @return:
        """
        def open_diags(deep_link):
            linkDict = parse_deep_link(deep_link)
            path = self.path_by_id(linkDict['pathid'])
            diags = path.find_diags(int(linkDict['startDate'])/1000, int(linkDict['endDate'])/1000)
            for diag in diags:
                url = create_url_diag(self.creds.pvc, self.id, diag['testId'],tab='data')
                open_web(url)
        w.input_window('Deep Link:', open_diags)

    def filtered_paths(self, filter):
        """
        Filter is a dictionary of Path characteristics. Find all paths that meet all filter criteria
        @param filter: dict of path characteristics wanted
        @return: list of Path objects that match filter
        """
        filtered_list = []
        for path in self.path_set:
            include = True
            for characteristic in filter:
                include = path[characteristic] == filter[characteristic] and include
        if include:
            filtered_list.append(path)
        return filtered_list

    def choose_path_by_ip(self):
        #Query user for IP address
        ip_needed = raw_input('Target IP address? ').rstrip()
        is_subnet = '/' in ip_needed
        paths = self.get_path_set()
        paths2 = []
        if is_subnet:
            subnet = ip.Ip4Subnet(ip_needed, 'Subnet')
        #Search thru looking for this IP address or subnet range
        #TODO This looks for paths with this range as target, need to expand to show source paths as well
        for path in paths:
            dst_ip = path.target_ip
            if is_subnet:
                try:
                    ip_decimal = ip.ipDDtoInt(dst_ip)
                    if ip_decimal > subnet.base and ip_decimal < subnet.top:
                        paths2.append(path)
                except:
                    print 'Can not evaulate dest address ' + dst_ip + ' , ignoring path.'
            else:
                if ip_needed == dst_ip:
                    paths2.append(path)
        paths3 = sorted(paths2, key=lambda k: k.pathName)
        if len(paths3) == 0:
            print 'No matching path found'
        else:
            pathNum = 0
            print
            for path in paths3:
                pathNum += 1
                print str(pathNum) + '\t' + path.pathName + '\t' + path.target_ip
            pathChoice = True
            while pathChoice:
                print
                pathChoice = raw_input('Open which path? ').rstrip()
                try:
                    pathCh = int(pathChoice)
                    if pathCh <= pathNum:
                        # pv.open_web(pv.create_url_path(pvc, paths3[pathCh-1]))
                        path.open_web()
                except:
                    if pathNum == 'q' or pathNum == 'Q' or pathNum == '' or pathNum == '0':
                        break


class Org_list():
    def __init__(self, creds):
        org_http = pathview_http('GET', 'pvc-data/v2/organization', creds)
        org_data = json.loads(org_http.data)
        self.org_list = []
        for org_dict in org_data:
                self.org_list.append(Org(org_dict, creds))


class Path():
    """
    This class represents a PathView path.  Upon creation pass in a dictionary that includes:
     pathName:'Path Name'
     target:'Target IP address'
     pathId: 'Path ID value'
     org: 'Organization to which the path belongs'
    """
    def __init__(self, org, path_dict):
        self.dict = path_dict
        self.pathName = path_dict['pathName']
        self.target_ip = path_dict['target']
        self.id = path_dict['id']
        self.org = org
        self.parameters = None
        self.diag_list = []

    def __repr__(self):
        return self.pathName

    def get_path_param(self, path_id):
        """
        Pull the details of a path (loss, jitter, RTT, etc).  Put details into the Path object and return
         details as a dict.  Why wouldn't this be inside the class?
        """
        if self.parameters == None:
            arguments = {'id':self.id}
            path_http = pathview_http('GET', 'pvc-data/v2/diagnostic/' + str(self.id), self.org.creds)
            self.parameters = json.loads(path_http.data)
        return self.parameters

    def open_web(self, start=None, end=None):
        """
        Create a url that will open this path page, and open it
        Default end time to now
        Default start time to 1 day before end time
        @param start: start time to display unix time
        @param end: end time to display unix time, default now
        """
        if end == None:
            end = int(time.time())
        end_ms = end * 1000 # milliseconds
        if start == None:
            start = end - (24 * 60 * 60) # one day
        start_ms = start * 1000
        pvc = self.org.creds.pvc
        url = create_url_path(pvc, self, start_ms, end_ms)
        open_web(url)

    def find_diags(self, start, end):
        """
        Find diagnostics that were executed on this specific path between the start and end times
        @param start: start of time window
        @param end: end of time window
        @return: list of Diag objects found in window
        https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2590&pathid=11866&startDate=1451050162122&endDate=1451053787270&loadSeqTz=false
        """
        payload = {'pathId':self.id,'from':start,'to':end}
        diag_http = pathview_http('GET', 'pvc-data/v2/diagnostic', self.org.creds, fields=payload)
        diag_dicts = json.loads(diag_http.data)
        diag_list = self.create_diags_from_dict_list(diag_dicts)
        return diag_list

    def create_diags_from_dict_list(self,diag_dict_list):
        return_set = []
        # for each dict on list
        while len(diag_dict_list) > 0:
            diag_dict = diag_dict_list[0]
            # check if it is already on self.diag_set
            diag = self.diag_on_list(diag_dict['testId'])
            if diag:
                # if yes, check if bidi on list, remove both
                return_set.append(diag)
                for x in range(1,len(diag_dict_list)):
                    if diag.bidi_id == diag_dict_list[x]['testId']:
                        diag_dict_list = diag_dict_list[:x] + diag_dict_list[x+1:]
                        break
                diag_dict_list = diag_dict_list[1:]
            # else (not in current set)
            else:
                # determine if bidi also on list
                found_bidi = False
                for x in range(1,len(diag_dict_list)):
                    diag_dict_nx = diag_dict_list[x]
                    if (abs(diag_dict['testId'] - diag_dict_nx['testId']) == 1) and \
                        ((diag_dict['target'] == diag_dict_nx['applianceNtwkInterface']) or \
                        (diag_dict['applianceNtwkInterface'] == diag_dict_nx['target'])):
                        # create one or two diags & put on list
                        new_diags = Diag(self, [diag_dict, diag_dict_nx])
                        # add to self.diag_set
                        self.diag_list.append(new_diags)
                        return_set.append(new_diags)
                        # remove from diag_dict_list
                        diag_dict_list = diag_dict_list[1:x] + diag_dict_list[x+1:]
                        found_bidi = True
                        break
                if not found_bidi:
                    new_diag = Diag(self,[diag_dict])
                    self.diag_list.append(new_diag)
                    return_set.append(new_diag)
                    diag_dict_list = diag_dict_list[1:]
        # return return_set
        return return_set

    def diag_on_list(self, diag_id):
        """
        check new diag against those on the list.  If not on list, add and return.  If on list, return the instance
          from the list so it is not duplicated
        @param new_diag:
        @return:
        """
        for diag in self.diag_list:
            if diag.id == diag_id:
                return diag
        return False


class Path_list():
    """
    Build a list of all paths in this org
    """
    def __init__(self, org, path_list):
        self.org = org
        self.path_list = path_list
        org.set_path_list(self)
    def __repr__(self):
        return "PathList for " + self.org


class Diag():
    """
    Create a Diagnostics object from Diag ID.  If there is a reverse direction diag associated with it, create that
      Diag object as well (recurse) and cross point using the self.bidi_id field
    """
    #TODO Can't find a way not to pull diag info twice.  Still not de-duping correctly.  Need to do it here I think.
    #TODO need to check path list before creating new Diag to see if it already exists, return existing one.
    #TODO can I return an old Diag from a Diag init?  Look at __new__ function.

    def __init__(self, path, diag_dicts):
        self.detail = None
        self.path = path
        self.org = path.org
        self.creds = self.org.creds
        self.bidi = None
        dual_diag = False
        if len(diag_dicts) == 1:
            diag_primary = diag_dicts[0]
        elif len(diag_dicts) == 2:
            diag_primary = diag_dicts[0]
            diag_reverse = diag_dicts[1]
            dual_diag = True
        else:
            raise ValueError ("more than two diagnostics found on diag get by ID")
        self.dict = diag_primary
        self.id = diag_primary['testId']
        if dual_diag:
            self.bidi_id = diag_reverse['testId']
            if self.bidi == None:
                self.bidi = Diag(self.path, [diag_reverse])
        self.name = self.dict['name']
        self.startTime = self.dict['startTime']
        self.detail = None

    def __repr__(self):
        return str(self.id)

    def get_detail(self):
        if self.detail == None:
            # https://polycom.pathviewcloud.com/pvc-data/v2/diagnostic/4021646/detail
            arguments = {'id':self.id}
            detail_http = pathview_http('GET', 'pvc-data/v2/diagnostic/' + str(self.id) + '/detail', self.creds, fields=arguments)
            detail_dicts = json.loads(detail_http.data)
            self.detail = detail_dicts[0]['hops']
            self.bidi.add_bidi_details(detail_dicts[1]['hops'])
        return self.detail

    def add_bidi_details(self, details):
        self.detail = details
    def qos_ok(self):
        hops = self.detail(self.creds)
        last_hop = hops[-1]
        if last_hop['qosValueSet'] == last_hop['qosValueMeasured']:
            return True
        else:
            return False

    def open_web(self, tab=0):
        """
        Create a url that will open a diagnostics page to the data detail, and open it
        @param tab: which diag tab to open (summary, data, voice)
        @return: text string which is url
        """
        pvc = self.path.org.creds.pvc
        open_web(pvc + '/pvc/emberview/testdetail/test/' + str(self.id) + '/' + tab)

class Alert():
    """
    Alert holds the details of a specific alert
    """
    def __init__(self, json_array):
        self.dict = json_array
        self.name = self.dict['name']
        self.id = self.dict['id']
    def __repr__(self):
        return self.name


class Alert_list():
    def __init__(self, org):
        arguments = {'orgId':org.id}
        alert_http = pathview_http('GET', 'pvc-data/v2/alertProfile', org.creds, fields=arguments)
        alert_dicts = json.loads(alert_http.data)
        self.alert_set = []
        for alert_dict in alert_dicts:
            self.alert_set.append(Alert(alert_dict))
    def find_alert(self, profile_name):
        """
        Search through alert_set, find alert that has name profile_name and return it
        @param profile_name: name of alert we want to find
        @param alert_set: list of Alerts
        @return: found Alert or False
        """
        for alert in self.alert_set:
            if alert.name == profile_name:
                return alert
        return False


def pathview_http(action, url, creds, fields={}, body=''):
    """
    Consolidation of requests to PVC so all error handling can be done here.
    @param action: 'GET' or 'POST'
    @param url: URL including pvc and specific components for this request
    @param fields: specific fields in dictionary form
    @param body:
    @return: return http response object
    """
    headers = urllib3.util.make_headers(basic_auth=creds.user + ':' + creds.password)
    url = creds.pvc + "/" + url
    try:
        return http.request(action, url, fields=fields, headers=headers, body=body)
    except requests.exceptions.Timeout:
        # Maybe set up for a retry, or continue in a retry loop
        print 'Network timeout, what is going on?'
        sys.exit(1)
    except urllib3.exceptions.SSLError as e:
        asdf = 1
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        print'Bad URL, try another?'
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        print e
        sys.exit(1)

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
    """
    Create a url that will open a diagnostics page to the data detail
    @param pvc: pathview cloud address
    @param orgId: organization ID (not needed?)
    @param diag_id: diagnostic id
    @param tab: which diag tab to open (summary, data, voice)
    @return: text string which is url
    """
    url = pvc + '/pvc/emberview/testdetail/test/' + str(diag_id) + '/' + tab
    return url

def create_url_diag2(diag, tab=0):
    """
    Create a url that will open a diagnostics page to the data detail
    @param pvc: pathview cloud address
    @param orgId: organization ID (not needed?)
    @param diag_id: diagnostic id
    @param tab: which diag tab to open (summary, data, voice)
    @return: text string which is url
    """
    pvc = diag.path.org.creds.pvc
    diag_id = diag.id
    url = pvc + '/pvc/emberview/testdetail/test/' + str(diag_id) + '/' + tab
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
    newPathDict['st'] = path.org.id
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
    """
    Create unix time from a datetime object
    @param dt:
    @return:
    """
    epoch = datetime.datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return int(delta.total_seconds()* 1000)


'''
def find_diags(creds, path_id, start, end):
    """
    Find diagnostics that were executed on this specific path between the start and end times
    @param creds:
    @param path_id:
    @param start:
    @param end:
    @return:
    """
    payload = {'pathId':path_id,'from':start,'to':end}
    diag_http = pathview_http('GET', 'pvc-data/v2/diagnostic', creds, fields=payload)
    diag_data = json.loads(diag_http.data)
    #TODO need to use (not yet created) diag list to de-dup this list, convert to diag class
    #TODO this should be inside the Path class
    return diag_data
'''

def open_web(url):
    new = 2 # open in a new tab, if possible
    webbrowser.open(url,new=new)

def parse_deep_link(deep_link):
    '''
    urllib3.util.parse_url(url)
        Given a url, return a parsed Url namedtuple. Best-effort is performed to parse incomplete urls. Fields not provided will be None.

        Partly backwards-compatible with urlparse.

        Example:

        >>> parse_url('http://google.com/mail/')
        Url(scheme='http', host='google.com', port=None, path='/', ...)
        >>> prase_url('google.com:80')
        Url(scheme=None, host='google.com', port=80, path=None, ...)
        >>> prase_url('/foo?bar')
        Url(scheme=None, host=None, port=None, path='/foo', query='bar', ...)
    '''
    #TODO consider using urllib3.util.parse_url for this function?
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

# def find_path_partial_name(partial, org):
#     paths = org.get_paths()
#     for path in paths:
#         if partial in path.pathName:
#             open_web(create_url_path(org.creds.pvc,path))

def open_diag_this_path_view(org):
    """
    https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2590&pathid=11866&startDate=1451050162122&endDate=1451053787270&loadSeqTz=false
    Using a deep link as input, find the diagnostic events in the viewed time window of this path
    @param creds:
    @return:
    """
    def open_diags(org, deep_link):
        link_dict = parse_deep_link(deep_link)
        path = org.path_by_id(link_dict['pathid'])
        if path == False:
            raise ValueError ('Could not find path by ID in this org')
        diags = path.find_diags(int(link_dict['startDate'])/1000, int(link_dict['endDate'])/1000)
        # diags = diag_de_dupe(diags)
        for diag in diags:
            diag.open_web(tab='data')
    w.input_window('Deep Link:', open_diags, org)

def paths_to_file(paths, filename):
    out_file = open(filename, 'wb')

    for path in paths:
        if 'qosName' in path.dict:
            qos = path.dict['qosName']
        else:
            qos = 'None'
        out_file.write(path.pathName + '\t' + path.ip + '\t' + path.dict['instrumentation'] + '\t' + path.dict['networkType'] + '\t' + path.dict['sourceAppliance'] + '\t' + qos + '\n')
    out_file.close()

'''
def create_path(path_dict, org):
    """
    Use path object information to initiate path on pathview cloud
    @param path: path object defining the path
    @return:True for success, False for failure
    """
    headers = urllib3.util.make_headers(basic_auth=org.creds.user + ':' + org.creds.password)
    url = org.creds.pvc + '/pvc-data/v2/path'
    headers['Content-Type'] = 'application/json'
    c_path_http =  http.request('POST', url, headers=headers, body=json.dumps(path_dict))
    c_path_data = json.loads(c_path_http.data)
    #TODO Now add path to path list in org
    return c_path_data
    '''

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

def diag_de_dupe(diag_list):
    dedupe_list = []
    for diag in diag_list:
        if diag not in dedupe_list and diag.bidi not in dedupe_list:
            dedupe_list.append(diag)
    return dedupe_list

