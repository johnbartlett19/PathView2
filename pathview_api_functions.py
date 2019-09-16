import requests, datetime, webbrowser, sys, json
import windows as w
import ip_address_functions as ip
import urllib, urllib3, certifi, time, locale

http = urllib3.PoolManager(
    cert_reqs = 'CERT_REQUIRED', #Force certificate check
    ca_certs=certifi.where(),  # Path to the Certifi bundle
)

# These are parameters of the pathview cloud.  The cloud will only respond to 50 requests in any 10 second window
# These are used by the bucket class to manage cloud requests
req_window = 10
req_per_window = 50

'''
API Documentation here:
https://polycom.pathviewcloud.com/pvc-data/swagger/#
'''

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
        self.bucket = Bucket(req_per_window,req_window)
        self.appliances = None

    def __repr__(self):
        return self.name

    def __lt__(self, other):
        return self.name < other.name

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
            path_set = pathview_http('GET', 'pvc-data/v2/path', self.creds, bucket=self.bucket, fields=payload)
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
        self.bucket.get_token()
        c_path_http =  http.request('POST', url, headers=headers, body=json.dumps(path_dict))
        if c_path_http.status > 399:
            http_data = json.loads(c_path_http.data)
            print(path_dict['pathName'] + ': ' + http_data['messages'][0])
            return False
        # elif c_path_data.reason == 'Created':
        #     print(path_dict['pathName'] + ': ' + c_path_http.reason)
        else:
            print(path_dict['pathName'] + ': Created')
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

    def get_appliances (self):
        """
        Get the appliance list from this org.  If the appliance list has not been created, create it first
        @return:
        """
        if self.appliances == None:
            self.init_appliances()
        return self.appliances

    def init_appliances (self):
        """
        Pull info from this org on all appliances and create a list of appliance objects self.path_set
        @return:
        """
        payload = {}
        payload['orgId'] = self.id
        page = 1
        paths = []
        appliance_http = pathview_http('GET', 'pvc-data/v2/appliance', self.creds, bucket=self.bucket, fields=payload)
        appliance_set = json.loads(appliance_http.data)
        self.appliances = []
        for appl in appliance_set:
            self.appliances.append(Appliance(self, appl))

    def open_org(self):
        base = self.creds.pvc + '/pvc/welcome.html'
        args = {}
        args['st'] = str(self.id)
        url = form_url(base, args)
        open_web(url)

    def open_diag_this_path_view(self):
        """
        https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2590&pathid=11866&startDate=1451050162122&endDate=1451053787270&loadSeqTz=false
        Using a deep link as input, find the diagnostic events in the viewed time window of this path
        @param creds:
        @return:
        """
        def open_diags(org, deep_link):
            linkDict = parse_deep_link(deep_link)
            path = self.path_by_id(linkDict['pathid'])
            diags = path.find_diags(int(int(linkDict['startDate'])/1000), int(int(linkDict['endDate'])/1000))
            for diag in diags:
                url = create_url_diag(org.creds.pvc, org.id, diag.id, tab='data')
                open_web(url)
        w.input_window('Deep Link:', open_diags, self)

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
        '''
        Input from user an IP address or a CIDER subnet
        Search through org paths for any path whose source or target matches the IP or subnet
        Display a list of those paths by name and allow the user to open them in a browser
        @return: nothing
        '''
        def match_ip (ipaddr, ip_needed, subnet=None):
            '''
            Determine if ipaddr matches target IP or subnet
            @param ipaddr: IP to check
            @param ip_neede:  IP address or CIDR subnet to match against
            @return: True for match, False otherwise
            '''
            if subnet:
                try:
                    ip_decimal = ip.ipDDtoInt(ipaddr)
                    if ip_decimal > subnet.base and ip_decimal < subnet.top:
                        return True
                except:
                    print('Can not evaulate dest address ' + ipaddr + ' , ignoring path.')
                    return False
            else:
                if ip_needed == ipaddr:
                    return True
            return False

        #Query user for IP address
        ip_needed = input('Target IP address? ').rstrip()
        paths = self.get_path_set()
        #Search thru looking for this IP address or subnet range in target
        paths2 = []
        # if match_ip()
        subnet = None
        is_subnet = '/' in ip_needed
        if  '/' in ip_needed:
            subnet = ip.Ip4Subnet(ip_needed, 'Subnet')
        for path in paths:
            if match_ip(path.target_ip, ip_needed, subnet=subnet):
                paths2.append(path)
            if path.interface:
                if match_ip(path.interface, ip_needed, subnet=subnet):
                    if path not in paths2:
                        paths2.append(path)
            else:
                for addr in path.appliance.local_net:
                    if match_ip(addr, ip_needed, subnet=subnet):
                        if path not in paths2:
                            paths2.append(path)

        # Sort paths into list and print for user
        paths3 = sorted(paths2, key=lambda k: k.pathName)
        if len(paths3) == 0:
            print('No matching path found')
        else:
            pathNum = 0
            print()
            for path in paths3:
                pathNum += 1
                print(str(pathNum) + '\t' + path.pathName + '\t' + path.target_ip)
            pathChoice = True
            while pathChoice:
                print()
                pathChoice = input('Open which path? ').rstrip()
                try:
                    pathCh = int(pathChoice)
                    if pathCh <= pathNum:
                        path.open_web()
                except:
                    if pathNum == 'q' or pathNum == 'Q' or pathNum == '' or pathNum == '0':
                        break

    def path_param_exceeds(self, measure, threshold, start=int(time.time())-60*60, end=int(time.time())):
        '''
        Find paths where the specified parameter (initially loss) exceeds the given threshold
        between start and end times (Unix seconds).  default to the last hour
        @param measure: what measure to look at (e.g. data packet loss)
        @param threshold: what threshold to test against (e.g. 1% loss)
        @param start: start time in unix seconds
        @param end: end time in unix seconds
        @return:
        '''
        paths = []
        for path in self.path_set:
            if path.dict['disabled']:
                print('Path ' + path.pathName + ' is disabled')
                continue
            print('Pulling stats on ' + path.pathName)
            perf_params = path.get_path_param()
            if perf_params:
                for minute in perf_params['data'][measure]:
                    found = False
                    if minute['value'] >= threshold:
                        paths.append(path)
                        found = True
                        break
                    if found:
                        break
        return paths

    def path_param_exceeds2(self, measure, threshold, start=int(time.time())-60*60, end=int(time.time())):
        '''
        Find paths where the specified parameter (initially loss) exceeds the given threshold
        between start and end times (Unix seconds).  default to the last hour
        This version pulls all the path parameters in one http pull
        @param measure: what measure to look at (e.g. data packet loss)
        @param threshold: what threshold to test against (e.g. 1% loss)
        @param start: start time in unix seconds
        @param end: end time in unix seconds
        @return:
        '''
        return_paths = []
        paths = self.get_path_set()
        # build list of path IDs
        id_list = []
        for path in paths:
            if not path.dict['disabled']:
                id_list.append(('pathIds',path.id))
        path_requests = urllib.parse.urlencode(id_list)
        url = 'pvc-data/v2/path/data' + '?' + path_requests
        req = pathview_http('GET', url, self.creds, bucket=self.bucket)
        data = json.loads(req.data)
        # Build a dictionary with results in form: key=pathId, value = dict
        param_dict = {}
        for params in data:
            param_dict[params['pathId']] = params
        # Go through path list:
        paths_with_params = []
        for path in paths:
            # Add values into path object if they are available
            if path.id in param_dict:
                path.set_path_parameters(param_dict[path.id])
                # Add that path to new list of paths to be evaluated below
                paths_with_params.append(path)
        paths = []
        for path in paths_with_params:
            perf_params = path.get_path_param()
            for minute in perf_params['data'][measure]:
                found = False
                if minute['value'] >= threshold:
                    paths.append(path)
                    found = True
                    break
                if found:
                    break
        return paths

    def find_paths_qos(self, by_hop=False):
        """
        build routine in org to search through paths and find paths with QoS change
        Distinguish between those that change end-to-end and those that change mid-path but correct by the end
        Pass back list of paths that meet criteria requested
        @param by_hop: find paths where QoS changes mid-path
        @param flush: flush out current diag data & refetch
        @return: list of path objects with QoS change
        """
        qos_path_list = []
        path_no_diag = []
        for path in self.path_set:
            if path.disabled == False:
                path.qos_change()
                if path.qos_consistent == False:
                    qos_path_list.append(path)
                elif (by_hop and path.qos_mid_change):
                    qos_path_list.append(path)
                elif path.qos_found_diag == False and path.disabled == False:
                    path_no_diag.append(path)
        return(qos_path_list, path_no_diag)


class Org_list():
    def __init__(self, creds):
        headers = {'key':'v3'}
        org_http = pathview_http('GET', 'api/v3/organization', creds, fields=headers)
        org_data = json.loads(org_http.data)
        self.org_list = []
        for org_dict in org_data:
                self.org_list.append(Org(org_dict, creds))

        # https://app-02.pm.appneta.com/api/v3/organization?api_key=v3
        # https://deloitteusasso.pm.appneta.com/api/v3/organization?api_key=v3

class Appliance():
    """
    This class represents an appliance attached to an org
    """
    def __init__(self, org, appl_dict):
        self.org = org
        self.dict = appl_dict
        self.name = appl_dict['name']
        self.conn_stat = appl_dict['connectionStatus']
        self.local_net = appl_dict['localNetworkInterfaces']

    def __repr__(self):
        return self.name


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
        self.qos_consistent = None
        self.qos_mid_change = None
        self.qos_changes = []
        self.qos_diag_time = None
        self.qos_found_diag = None
        self.disabled = path_dict['disabled']
        self.alertProfileId = path_dict['alertProfileId']
        self.interface = path_dict['applianceInterface']
        for appliance in self.org.get_appliances():
            if appliance.name == path_dict['sourceAppliance']:
                self.appliance = appliance
                break

    def __repr__(self):
        return self.pathName

    def set_path_parameters(self, parameters):
        """
        If path parameters have been obtained in bulk, use this function to stuff them into the objects
        @param parameters: dictionary of parameters. Overwrites any existing parameters
        @return:
        """
        self.parameters = parameters

    def get_path_param(self):
        """
        Pull the details of a path (loss, jitter, RTT, etc).  Put details into the Path object and return
         details as a dict.
        """
        if self.parameters == None:
            try_count = 4
            success = False
            while not success:
                try:
                    path_http = pathview_http('GET', 'pvc-data/v2/path/' + str(self.id) + '/data', self.org.creds, bucket=self.bucket,)
                    self.parameters = json.loads(path_http.data)
                    success = True
                except:
                    try_count -= 1
                    if try_count == 0:
                        print('*** Unable to pull data for path ' + self.pathName + ' ***')
                        return False
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

    def find_diags(self, start, end, limit=None):
        """
        Find diagnostics that were executed on this specific path between the start and end times
        @param start: start of time window
        @param end: end of time window
        @return: list of Diag objects found in window
        https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2590&pathid=11866&startDate=1451050162122&endDate=1451053787270&loadSeqTz=false
        """
        payload = {'pathId':self.id,'from':start,'to':end}
        if limit != None:
            payload['limit'] = limit
        diag_http = pathview_http('GET', 'pvc-data/v3/diagnostic', self.org.creds, bucket=self.org.bucket, fields=payload)
        if diag_http.data == '' or diag_http.data == '[]':
            return False
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
                    if diag.bidi and diag.bidi.id == diag_dict_list[x]['testId']:
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

    def qos_change(self):
        """
        build routine in Path class that will find a recent diagnostic, determine QoS changes, and store as local values
        Need:  qos_consistent (True or False)
                qos_changes[(hop, value) where hop is 0 to N and value is 'AF41' etc.
        This routine takes a 'flush=True' input to force it to go get new data
        If this routine has no data it goes to get new data
        If the data is more than an hour old, it goes to get new data
        @param flush: if True, clear out current data (if any) and fetch new from cloud
        @return: True or False to include this path in the list
        """
        '''
        Pull most recent diag from web
        '''
        fetch_count = 6
        days_history = 120
        now = unix_time(datetime.datetime.utcnow())
        # Go get most recent diag
        start = now - days_history*24*3600
        # Pull most recent diagnostic
        diag_list = self.find_diags(start, now, limit=fetch_count)
        if len(diag_list) == 0:
            print('*** For path ' + self.pathName + ' no diagnostic available within 60 days ***')
            self.qos_found_diag = False
            return False
        diag = diag_list[0]
        print('For path ' + self.pathName + ' found diag that started at ' + time_to_str(diag.startTime) + ' UTC')
        '''
        Now pull diag statistics and determine qos change information
        '''
        details = False
        using_diag = 0
        while details == False:
            details = diag.get_detail()
            if details == False:
                using_diag += 1
                if using_diag == fetch_count or using_diag == len(diag_list):
                    print('*** Unable to find good diag within latest ' + str(fetch_count) + ' diags on path ' + self.pathName + ' ***')
                    self.qos_found_diag = False
                    return False
                print('*** Unable to pull stats on diag for ' + self.pathName + ' evaluating previous diag ***')
                diag = diag_list[using_diag]
        self.qos_found_diag = True
        hop_count = len(details)
        if details[hop_count-1]['qosValueMeasured'] == details[hop_count-1]['qosValueSet']:
            self.qos_consistent = True
        else:
            self.qos_consistent = False
        self.qos_changes = [details[0]['qosValueSet']]
        self.qos_mid_change = False
        for hop in range(hop_count - 1):
            self.qos_changes.append((hop + 1, details[hop]['qosValueMeasured']))
            if details[0]['qosValueMeasured'] != details[hop]['qosValueMeasured'] and \
                    (not (details[hop]['qosValueMeasured'] == -1)):
                self.qos_mid_change = True

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
        # fmt = '%Y-%m-%dT%H:%M:%S.%f'
        self.startTime = self.dict['startTime']
        self.detail = None
        self.test_status = diag_dicts[0]['testStatus']

    def __repr__(self):
        return str(self.id)

    def get_detail(self):
        if self.test_status == 'Failed':
            return False
        if self.detail == None:
            # https://polycom.pathviewcloud.com/pvc-data/v2/diagnostic/4021646/detail
            arguments = {'id':self.id}
            detail_http = pathview_http('GET', 'pvc-data/v2/diagnostic/' + str(self.id) + '/detail', self.creds, bucket=self.org.bucket,  fields=arguments)
            if detail_http.data == '':
                return False
            detail_dicts = json.loads(detail_http.data)
            self.detail = detail_dicts[0]['hops']
            if self.detail == []:
                return False
            # if self.bidi:
            #     self.bidi.get_detail()
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
        alert_http = pathview_http('GET', 'pvc-data/v2/alertProfile', org.creds, bucket=org.bucket, fields=arguments)
        alert_dicts = json.loads(alert_http.data)
        self.alert_set = []
        for alert_dict in alert_dicts:
            self.alert_set.append(Alert(alert_dict))
    def find_by_name(self, profile_name):
        """
        Search through alert_set, find alert that has name profile_name and return it
        @param profile_name: name of alert we want to find
        @return: found Alert or False
        """
        for alert in self.alert_set:
            if alert.name == profile_name:
                return alert
        return False
    def find_by_id(self, profile_id):
        """
        Search through alert_set, find alert that has name profile_id and return it
        @param profile_id: id of alert we want to find
        @return: found Alert or False
        """
        for alert in self.alert_set:
            if alert.id == profile_id:
                return alert
        return False


def pathview_http(action, url, creds, bucket=None, fields={}, body=''):
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
    if bucket != None:
        bucket.get_token()
    try:
        http_resp =  http.request(action, url, fields=fields, headers=headers, body=body)
        if http_resp.reason == 'Too Many Requests':
            raise ValueError ('Overrunning service, bucket not working correctly')
        if http_resp.status >= 400:
            raise ValueError('HTTP Response: ' + str(http_resp.status) + ' - ' + http_resp.msg)
        return http_resp
    except requests.exceptions.Timeout:
        # Maybe set up for a retry, or continue in a retry loop
        print('Network timeout, what is going on?')
        sys.exit(1)
    except urllib3.exceptions.SSLError as e:
        asdf = 1
    except requests.exceptions.TooManyRedirects:
        # Tell the user their URL was bad and try a different one
        print('Bad URL, try another?')
        sys.exit(1)
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        print(e)
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
    return int(delta.total_seconds())

def time_to_str(date_time_value):
    if type(date_time_value) is str:
        date_time_value = int(str)
    if type(date_time_value) is int:  #was is long:
        if date_time_value > 10^12:
            date_time_value = date_time_value / 1000
        time_dt = datetime.datetime.fromtimestamp(date_time_value)
        # print(datetime.datetime.fromtimestamp(int("1284101485")).strftime('%Y-%m-%d %H:%M:%S')))
    elif (type(date_time_value) is datetime.datetime):
        time_dt = time
    else:
        raise ValueError('Did not recognize time value as Unix or datetime')
    fmt = '%Y-%m-%d %H:%M:%S'
    return time_dt.strftime(fmt)


def open_web(url):
    new = 2 # open in a new tab, if possible
    webbrowser.open(url,new=new)


def parse_deep_link(deep_link):
    """
    Input a deep link copied from GUI and parse through to find the lookup components like
    org id, path id, etc.  Return as a dictionary.
    @param deep_link: Deep link from paste window
    @return: dict of value names and values
    """
    url, args = deep_link.split('?')
    arg_list = args.split('&')
    arg_dict = {}
    for arg in arg_list:
        name, value = arg.split('=')
        arg_dict[name] = value
    return  arg_dict


def get_start_end():
    deep_link = input('Deep link: ')
    link_dict = parse_deep_link(deep_link)
    return (link_dict['startDate'],link_dict['endDate'])

# def find_path_partial_name(partial, org):
#     paths = org.get_paths()
#     for path in paths:
#         if partial in path.pathName:
#             open_web(create_url_path(org.creds.pvc,path))

# def open_diag_this_path_view(org):
#     """
#     https://polycom.pathviewcloud.com/pvc/pathdetail.html?st=2590&pathid=11866&startDate=1451050162122&endDate=1451053787270&loadSeqTz=false
#     Using a deep link as input, find the diagnostic events in the viewed time window of this path
#     @param creds:
#     @return:
#     """
#     def open_diags(org, deep_link):
#         link_dict = parse_deep_link(deep_link)
#         path = org.path_by_id(link_dict['pathid'])
#         if path == False:
#             raise ValueError ('Could not find path by ID in this org')
#         diags = path.find_diags(int(link_dict['startDate'])/1000, int(link_dict['endDate'])/1000)
#         # diags = diag_de_dupe(diags)
#         for diag in diags:
#             diag.open_web(tab='data')
#     w.input_window('Deep Link:', open_diags, org)

def paths_to_file(paths, filename):
    """
    Get all the paths in the org and write them out to a file.
    Just used this once to solve a problem for Polycom IT?
    @param paths:
    @param filename:
    @return:
    """
    out_file = open(filename, 'wb')

    for path in paths:
        if 'qosName' in path.dict:
            qos = path.dict['qosName']
        else:
            qos = 'None'
        out_file.write(path.pathName + '\t' + path.ip + '\t' + path.dict['instrumentation'] + '\t' + path.dict['networkType'] + '\t' + path.dict['sourceAppliance'] + '\t' + qos + '\n')
    out_file.close()


def find_org(org_name, org_set):
    """
    Given name of org, search org set for org with name and return Org
    @param org_name: text string org name
    @param org_set:
    @return:
    """
    for org in org_set:
        if org.name == org_name:
            return org
    return False

'''

Routine for leaky bucket

Set local variable for time now.
Keep variable for time last entered this routine
Add tokens into the bucket based on how many milliseconds have elapsed since last entered
Remove token for this request if available.
If not available, delay until a token is available.  Can be calculated based on time constants
'''
class Bucket():
    """
    Class to implement a delay queue of length req_per_window  Calls to bucket.get_token() will return immediately
     if fewer than req_per_window (integer) calls were made during the last req_window (seconds).  If too many requests
     have been made, bucket.get_token() sleeps until oldest request was at least req_window seconds before.  This
     routine is synchronous and blocks execution.
    """
    def __init__(self, req_per_window, req_window):
        self.req_per_window = int(req_per_window * 0.96)
        self.req_window = req_window
        self.queue = [datetime.datetime.utcnow()]

    def get_token(self):
        now = datetime.datetime.utcnow()
        if len(self.queue) < self.req_per_window:
            self.queue.append(now)
        elif len(self.queue) == self.req_per_window:
            oldest = self.queue[0]
            self.queue = self.queue[1:]
            delta = now - oldest
            delta_sec = (now - oldest).total_seconds()
            if delta_sec < self.req_window:
                sleep_time = self.req_window - delta_sec
                time.sleep(sleep_time)
                now = datetime.datetime.utcnow()
            self.queue.append(now)
        else:
            raise ValueError ('Bucket queue too long !!!')
        return True


def reencode(file):
    for line in file:
        yield line.decode(locale.getpreferredencoding()).encode('ascii', 'replace')


def list_and_choose_path(description, path_list, window_param=None):
    """
    Takes a list of paths and a description.  Prints out description, then lists paths with an index so user
    can choose which path to display.  If user chooses a path, opens the web page associated with that path.
    Stays in this routine until user chooses '0', q etc. or provides no answer, then exits back to calling routine
    @param description: Text string to be printed before listing paths
    @param path_list: list of path objects [path1, path2, path3 ..]
    @return:
    """
    if window_param:
        start, end = view_window(window_param)
    pathNum = 0
    print()
    print(description)
    print()
    for path in path_list:
        pathNum += 1
        print(str(pathNum) + '\t' + path.pathName)
    while True:
        path_choice = input('Open a path? ').rstrip()
        if path_choice.lower() in ['q', '', '0', 'quit']:
            break

        if path_choice in ['all']:
            for path in path_list:
                path.open_web(start=start, end=end)
            break
        try:
            path_choice = int(path_choice)
        except:
            break
        if path_choice <= pathNum and path_choice > 0:
            path_to_open = path_list[path_choice-1]
            path_to_open.open_web(start=start, end=end)

def view_window(window_param):
    size, unit = window_param
    end_sec = int(time.time())
    if unit not in ['sec', 'min', 'hour', 'day', 'month']:
        raise ValueError("Don't recognize unit of time " + unit)
    elif unit == 'sec':
        multiplier = 1
    elif unit == 'min':
        multiplier = 60
    elif unit == 'hour':
        multiplier = 60*60
    elif unit == 'day':
        multiplier = 60*60*24
    elif unit == 'month':
        multiplier = 60*60*24*30
    return (end_sec - multiplier * size, end_sec)
