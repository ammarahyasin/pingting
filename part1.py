#!/usr/bin/env python3

# -*- coding: UTF-8 -*-

######
import argparse
import socket
import os
import sys
import struct
import time


def setupArgumentParser() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='A collection of Network Applications developed for SCC.203.')
    parser.set_defaults(func=ICMPPing, hostname='lancaster.ac.uk')
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_p = subparsers.add_parser(
        'ping', aliases=['p'], help='run ping')
    parser_p.add_argument('hostname', type=str,
                          help='host to ping towards')
    parser_p.add_argument('count', nargs='?', type=int,
                          help='number of times to ping the host before stopping')
    parser_p.add_argument('timeout', nargs='?',
                          type=int,
                          help='maximum timeout before considering request lost')
    parser_p.set_defaults(func=ICMPPing)

    parser_t = subparsers.add_parser('traceroute', aliases=['t'],
                                     help='run traceroute')
    parser_t.add_argument('hostname', type=str,
                          help='host to traceroute towards')
    parser_t.add_argument('timeout', nargs='?', type=int,
                          help='maximum timeout before considering request lost')
    parser_t.add_argument('protocol', nargs='?', type=str,
                          help='protocol to send request with (UDP/ICMP)')
    parser_t.set_defaults(func=Traceroute)

    args = parser.parse_args()
    return args


class NetworkApplication:

    def checksum(self, dataToChecksum: str) -> str:
        csum = 0
        countTo = (len(dataToChecksum) // 2) * 2
        count = 0

        while count < countTo:
            thisVal = dataToChecksum[count+1] * 256 + dataToChecksum[count]
            csum = csum + thisVal
            csum = csum & 0xffffffff
            count = count + 2

        if countTo < len(dataToChecksum):
            csum = csum + dataToChecksum[len(dataToChecksum) - 1]
            csum = csum & 0xffffffff

        csum = (csum >> 16) + (csum & 0xffff)
        csum = csum + (csum >> 16)
        answer = ~csum
        answer = answer & 0xffff
        answer = answer >> 8 | (answer << 8 & 0xff00)
        answer = socket.htons(answer)
        return answer

    def printOneResult(self, destinationAddress: str, packetLength: int, time: float, ttl: int, destinationHostname=''):

        if destinationHostname:
            print("%d bytes from %s (%s): ttl=%d time=%.2f ms" % (
                packetLength, destinationHostname, destinationAddress, ttl, time))
        else:
            print("%d bytes from %s: ttl=%dtime=%.2f ms" %
                  (packetLength, destinationAddress, ttl, time))

    def printAdditionalDetails(self, packetLoss=0.0, minimumDelay=0.0, averageDelay=0.0, maximumDelay=0.0):
        print("%.2f%% packet loss" % (packetLoss))
        if minimumDelay > 0 and averageDelay > 0 and maximumDelay > 0:
            print("rtt min/avg/max = %.2f/%.2f/%.2fms" %
                  (minimumDelay, averageDelay, maximumDelay))


class ICMPPing(NetworkApplication):

    def receiveOnePing(self, icmpSocket, destinationAddress, ID, timeout, icmpHeader):

        # 1. Wait for the socket to receive a reply. #2. Once received, record time of receipt, otherwise, handle a timeout
        #try:
        timeRecieved = time.time()
        information, address = icmpSocket.recvfrom(1024)
            
        # 3. Compare the time of receipt to time of sending, producing the total network delay
        timeSent= self.sendOnePing(icmpSocket, destinationAddress, 111)
        totalNetworkDelay = (timeRecieved*1000) - timeSent[0]
            
        # 4. Unpack the packet header for useful information, including the ID
        icmpType, icmpCode, icmpChecksum, icmpPacketID, icmpSeqNumber = struct.unpack("bbHHh", icmpHeader)

        # 5. Check that the ID matches between the request and reply AND THEN 6. Return total network delay
        originalID = timeSent[2]
        if(icmpPacketID == originalID):
            return totalNetworkDelay


    def sendOnePing(self, icmpSocket, destinationAddress, ID):
        # 1. Build ICMP header
        icmpHeader=struct.pack("bbHHh", 8, 0, 0, ID, 1)
        # 2. Checksum ICMP packet using given function
        icmpChecksum = self.checksum(icmpHeader)
        # 3. Insert checksum into packet
        icmpHeader = struct.pack("bbHHh", 8, 0, icmpChecksum, ID, 1)
        # 4. Send packet using socket- double check this //run with wireshark
        icmpSocket.sendto(icmpHeader, (destinationAddress, 1))
        # 5. Record time of sending
        timeSent=time.time()
        return timeSent, icmpHeader, ID

    def doOnePing(self, destinationAddress):
        # 1. Create ICMP socket
        # Translate an Internet protocol name (for example, 'icmp') to a constant suitable for passing as the (optional) third argument to the socket() function.
        icmp_proto = socket.getprotobyname("icmp") #debugging
        icmpSocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp_proto)
        #icmpSocket = socket.socket(socket.AF_INET,socket.SOCK_RAW, socket.IPPROTO_ICMP)
        icmpSocket.bind(('', 1534))
        #print("Ping server ready on port", 1534)
        # 2. Call sendOnePing function
        timeSent = self.sendOnePing(icmpSocket, destinationAddress, 111)
        # 3. Call receiveOnePing function
        networkDelay = self.receiveOnePing(icmpSocket, destinationAddress, 111, 1000, timeSent[1])

        # 4. Close ICMP socket
        icmpSocket.close()

        # 5. Return total network delay
        return networkDelay

    def __init__(self, args):
        print('Ping to: %s...' % (args.hostname))
        # 1. Look up hostname, resolving it to an IP address
        ipAddress = socket.gethostbyname(args.hostname)

        # 2. Call doOnePing function approximately every second
        while True:
            time.sleep(1)
            #print("testing:", ipAddress)
            returnedDelay = self.doOnePing(ipAddress)
            # 3. Print out the returned delay (and other relevant details) using the printOneResult method
            self.printOneResult(ipAddress, 50, returnedDelay, 150)
            #Example use of printOneResult - complete as appropriate
            # 4. Continue this process until stopped - did this through the while True
            break


class Traceroute(NetworkApplication):

    def pingEachNode(self, ipAddress, numberOfNodes):
        # 1. Create ICMP socket
        icmp_proto = socket.getprotobyname("icmp") #debugging
        #icmpSocket= socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp_proto)
        icmpSocket = socket.socket(socket.AF_INET,socket.SOCK_RAW,socket.IPPROTO_ICMP)

        # 2. Call sendNodePing function
        #print('socket: ', icmpSocket, 'ipAddy: ',ipAddress) #debugging
        timeSent, icmpHeader = self.sendNodePing(icmpSocket, ipAddress) #NOTE: need IP adress as second parameter but throwing up errors
        # 3. Call recieveNodePing function to get the node delays, ICMP type and TTL 
        nodeDelaysList, TTL ,icmpType, packetLength  = self.recieveNodePing(icmpSocket, icmpHeader, 111, 1000, timeSent)
        #nodeDelaysList = pingFunction[0]
        #TTL = pingFunction[1]
        # 4. Close ICMP socket
        icmpSocket.close()
        # 5. Return total network delay- add up all the nodes
        x = 0
        for x in (nodeDelaysList): #iterate over list items and add them  up 
            totalDelay = sum(nodeDelaysList)
            x = x + 1
            if x == (len(nodeDelaysList)+1): #add 1 because index starts from 0
                break
            return totalDelay, TTL, icmpType, packetLength

    def sendNodePing(self, icmpSocket, ipAddress):
        # 1. Build ICMP header
        ID = 111
        icmpHeader= struct.pack("bbHHh", 8, 0, 0, ID, 1)
        TTL = 1 #setting initial TTL value to 1 using setsockopt
        #icmpSocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, TTL)
        icmpSocket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, TTL)
    
        # 2. Checksum ICMP packet using given function
        icmpChecksum= self.checksum(icmpHeader)
         # 3. Insert checksum into packet
        packetHeader= struct.pack("bbHHh", 8, 0, icmpChecksum, ID, 1)
        packet= packetHeader
        # 4. Send packet using socket
        # double check this //run with wireshark
        icmpSocket.sendto(packet, (ipAddress, 1)) #ipAddy and 1 make up the IPadress and port number
        # 5. Record time of sending
        sentTime= time.time()
        return sentTime, icmpHeader

    def recieveNodePing(self, icmpSocket, icmpHeader, ID, timeout, timeSent):
        # 1. Wait for the socket to receive a reply- TTL = 0
        information, address = icmpSocket.recvfrom(1024)
        TTL = 0; 
        #print("TTL is:", TTL)
        icmpSocket.settimeout(timeout)

        # 2. Once received, record time of receipt, otherwise, handle a timeout
        try:  # TTL == 0
            #icmpSocket.connect(self.hostname, self.port)
            timeRecieved = time.time()
            nodeDelaysList = [] 
            # 3. Compare the time of receipt to time of sending, producing the total network delay- did when calculated RTT? 
            oneNodeDelay = (timeRecieved) - timeSent
            # 4. Unpack the packet header for useful information, including the ID
            icmpType, icmpCode, icmpChecksum, icmpPacketID, icmpSeqNumber= struct.unpack("bbHHh", icmpHeader)
            packetLength = len(icmpHeader)
            #print("packetID: ", icmpPacketID)
            #print("ID: ", ID)
            #print("packetLength: ", packetLength)
            # 5. Check that the ID matches between the request and reply and # 6. Return total network delay
            if(icmpPacketID == ID):
                nodeDelaysList.append(oneNodeDelay)
                TTL = TTL+1
                #print("new TTL is: ", TTL)
                print("list: ", nodeDelaysList)
                return nodeDelaysList, TTL, icmpType, packetLength
            else:
                errorMessage = print("ID's don't match, sorry g")
                nodeDelaysList.append(errorMessage)
                return nodeDelaysList, TTL , icmpType, packetLength
        
        except socket.timeout:  #if nothing is recieved, handle a timeout
            print("Socket has not recieved a reply")
            return None
    
    def __init__(self, args):
        # Please ensure you print each result using the printOneResult method!
        print('Traceroute to: %s...' % (args.hostname))
        # 1. Look up hostname, resolving it to an IP address
        ipAddress= socket.gethostbyname(args.hostname)
        numberofNodes= 0  # create variable and initialise
        # 2. Call pingEachNode function approximately every second
        while True:
            time.sleep(1)
            #nodalDelay = self.pingEachNode(ipAddress, args.timeout, 1)        
            nodalDelay, TTL, icmpType, packetLength = self.pingEachNode(ipAddress, numberofNodes)
            #self.printOneResult(ipAddress, 50, nodalDelay[1]*1000, 150)
            numberofNodes = numberofNodes + 1  # increments number of nodes
            
            # 4. Continue this process until stopped - until icmpType = 11
            if icmpType == 11:
                print("ICMP Port Unreachable message: final node reached")
                return False
            # 3. Print out the returned delay (and other relevant details) using the printOneResult method
            self.printOneResult(ipAddress, packetLength, (nodalDelay*1000), TTL, args.hostname)    
        
        
        
if __name__ == "__main__":
    args= setupArgumentParser()
    args.func(args)

def main():
    print("running")
    NetworkApplication()