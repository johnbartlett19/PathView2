__author__ = 'jbartlett'

'''
create subnet type
name - use name in PolycomSubnets.csd file as location
create for subnet type ability to determine if an ip is in that subnet
cache the answer for speed

input subnets from 'PolycomSubnets.csd' and create instances

parse through CDR file, find unique system names, find IP address
 and determine their subnet range name

Create output file that maps endpoint name to location
FredHDX, Vatican City
MoscowOTX1, Moscow

'''

import csv

def ipIntToDD(ipAddr):
    ''' Convert integer value < 2^32 to dotted-decimal IP address string
        input: integer < 2^32
        output: string (e.g. '10.25.13.127')
    '''
    a = ipAddr >> 24
    b = ipAddr >> 16 & 255
    c = ipAddr >> 8 & 255
    d = ipAddr & 255
    return str(a) + '.' + str(b) + '.' + str(c) + '.' + str(d)

# Routine to convert dotted-decimal-string to integer
def ipDDtoInt(ipAddr):
    ''' Convert dotted-decimal IP address string to an integer
        Input: dotted-decimal string (e.g. '10.25.13.127') or integer < 2^32
        output: integer
    '''
    if type(ipAddr) == str:
        (a,b,c,d) = ipAddr.split('.')
        intAddr = (int(a) << 24) + (int(b) << 16) + (int(c) << 8) + int(d)
    elif type(ipAddr) == int and ipAddr < (2**32):
        intAddr = ipAddr
    else:
        raise ValueError('not dotted decimal or integer out of range')
    return intAddr

def sortIpAddr(ipAddrList):
    ''' Input is a list of strings of dotted decimal ip addresses
        e.g. ['10.5.14.12', '172.13.4.16', '192.168.27.54']
        Output is the same list, but sorted by decimal value in each octet
    '''
    intDict = {}
    sortedList= []
    for addr in ipAddrList:
        intDict[ipDDtoInt(addr)] = addr
    for intAdd in sorted(intDict):
        sortedList.append(intDict[intAdd])
    return sortedList

def findBase(cidrSub):
    addr, cidr = cidrSub.split('/')
    inAddr = ipDDtoInt(addr)
    inAddrMask = (2**int(cidr)-1)<<(32-int(cidr))
    inAddrBase = inAddr & inAddrMask
    #addrb = ipIntToDD(inAddrBase)
    #print addr, cidr, inAddr, inAddrMask, inAddrBase, addrb
    return inAddrBase

def findTop(cidrSub):
    base = findBase(cidrSub)
    addr, cidr = cidrSub.split('/')
    size = 2**(32-int(cidr)) - 1
    top = base + size
    return top

class Ip4Subnet(object):
    ''' an IPV4 subnet '''
    def __init__(self, cidrSub, name):
        ''' expecting input in the form 192.168.2.0/24'''
        # init a subnet with some stuff
        self.cidr = cidrSub
        self.base = findBase(self.cidr)
        self.top = findTop(self.cidr)
        self.name = name

    def __str__(self):
        # create string for printout
        return str(self.cidr)

    def getBase(self):
        return self.base

    def getTop(self):
        return self.top

    def isIn(self, ipAddr):
        ''' determine if submitted IP address is in this subnet
            input assumed to be a long integer, not dotted decimal string'''
        try:
            aa = ipAddr + 0
        except:
            raise ValueError('Expecting integer not dotted decimal string')
        return ipAddr >= self.base and ipAddr <= self.top

def getSubnets(inFileName):
    inFile = open(inFileName, 'rb')
    lineNum = 0
    subnets = []
    for row in inFile:
        lineNum += 1
        #print row
        row = row.strip()
        if lineNum > 1:
            subnet, name = row.split(',')
            #print subnet, name

            aa = Ip4Subnet(subnet, name)
            subnets.append(aa)
    return subnets

def findSubnet(ipAddr, subnets):
    for sub in subnets:
        if sub.isIn(ipDDtoInt(ipAddr)):
            return sub
    #print 'LineNumber', lineNum, 'Addr: ', ipIntToDD(ipAddr)
    raise ValueError('Subnet not found')

#def main():
#    inFileName = 'PolycomSubnets.csv'
#    subnets = getSubnets(inFileName)
#
#    inEndpointName = 'CombinedEndpoints.csv'
#    inEndpointFile = open(inEndpointName, 'rb')
#    inEndpointReader = csv.reader(inEndpointFile, dialect='excel', delimiter=',', quotechar='"')
#
#    outEndpointName = 'CombinedEndpointsOut.csv'
#    outEndpointFile = open(outEndpointName, 'wb')
#    outEndpointWriter = csv.writer(outEndpointFile, dialect='excel', delimiter=',', quoting=csv.QUOTE_MINIMAL)
#    lineNum = 0
#
#    outErrorName = 'subnetNotFound.csv'
#    outErrorFile = open(outErrorName, 'wb')
#    #outERrorWriter = csv.writer(outErrorFile, dialect='excel', delimiter=',', quoting=csv.QUOTE_MINIMAL)
#
#    for row in inEndpointReader:
#        lineNum += 1
#        if lineNum > 1:
#            try:
#                sub = findSubnet(ipDDtoInt(row[1]), subnets)
#                row.append(sub.name)
#                outEndpointWriter.writerow(row)
#            except ValueError:
#                outErrorFile.write(row[1] + ',' + row[0] + '\n')
#
#
#    inEndpointFile.close()
#    outEndpointFile.close()
#    outErrorFile.close()
#
##main()
#
#inFileName = 'PolycomSubnets.csv'
#subnets = getSubnets(inFileName)
#
#inAddrName = raw_input('Filename to process? ')
#outFileName = 'Out_' + inAddrName
#outFile = open(outFileName, 'wb')
#inAddr = open(inAddrName, 'rb')
#for addr in inAddr:
#    addr = addr.strip()
#    sub = findSubnet(addr, subnets)
#    outStr = addr + ',' + sub.name + '\n'
#    print addr, sub.name
#    outFile.write(outStr)
#outFile.close()
#inAddr.close()
