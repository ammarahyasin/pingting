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
            print("%d bytes from %s (%s):ttl=%d time=%.2f ms" % (
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
            #timeSent = information
            #print(information)
            
            # 3. Compare the time of receipt to time of sending, producing the total network delay
        timeSent= self.sendOnePing(icmpSocket, destinationAddress, 111)
        totalNetworkDelay = (timeRecieved*1000) - timeSent[0]
            
            # 4. Unpack the packet header for useful information, including the ID
        icmpType, icmpCode, icmpChecksum, icmpPacketID, icmpSeqNumber = struct.unpack("bbHHh", icmpHeader)

            # 5. Check that the ID matches between the request and reply AND THEN 6. Return total network delay
        originalID = timeSent[2]
        if(icmpPacketID == originalID):
            return totalNetworkDelay

            #else:
                #return 0


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
        print("Ping server ready on port", 1534)
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
            #debuggingTimeout = args.timeout
            print("testing:", ipAddress)
            returnedDelay = self.doOnePing(ipAddress)
            # 3. Print out the returned delay (and other relevant details) using the printOneResult method
            self.printOneResult(ipAddress, 50, returnedDelay, 150)
            #Example use of printOneResult - complete as appropriate
            # 4. Continue this process until stopped - did this through the while True


class Traceroute(NetworkApplication):

    def __init__(self, args):
    #
        # Please ensure you print each result using the printOneResult method!
        print('Traceroute to: %s...' % (args.hostname))
        # 1. Look up hostname, resolving it to an IP address
        ipAddress= socket.gethostbyname(args.hostname)
        numberofNodes= 0  # create variable and initialise
        # 2. Call PingOneNode function approximately every second
        while True:
            time.sleep(1)
            #nodalDelay = self.pingOneNode(ipAddress, args.timeout, 1)
            
            nodalDelay = self.pingOneNode(ipAddress)
            self.printOneResult(ipAddress, 50, nodalDelay[1]*1000, 150)
            numberofNodes = numberofNodes + 1  # increments number of nodes
            
            # 4. Continue this process until stopped - until ICMP = 0
            if self.ICMP_CODE == 0:
                break
            # 3. Print out the returned delay (and other relevant details) using the printOneResult method
            # check this don't think its right
            self.printOneResult(ipAddress, 50, nodalDelay[1]*1000, 150)

    def pingOneNode(self, ipAddress):
        # 1. Create ICMP socket
        icmp_proto = socket.getprotobyname("icmp") #debugging
        icmpSocket= socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp_proto)
        # 2. Call sendNodePing function
        timeSent= self.sendNodePing(icmpSocket, ipAddress)
        # 3. Call recieveNodePing function
        networkDelay= self.recieveNodePing(icmpSocket, ipAddress, 111, 1000, timeSent)
         # 4. Close ICMP socket
        icmpSocket.close()
        # 5. Return total network delay- add up all the nodes
        x = 0 
        for x in self.numberOfNodes:
            totalDelay = (networkDelay[x] + networkDelay[x + 1])
            x = x + 1
            if x == self.numberOfNodes:
                break
            return totalDelay

    def sendNodePing(icmpSocket, ipAddress):
         # 1. Build ICMP header
        icmpHeader= struct.pack("bbHHh", 8, 0, 0, ID, 1)
        # 2. Checksum ICMP packet using given function
        icmpChecksum= self.checksum(icmpHeader)
         # 3. Insert checksum into packet
        packetHeader= struct.pack("bbHHh", 8, 0, icmpChecksum, ID, 1)
        packet= packetHeader
        # 4. Send packet using socket
        # double check this //run with wireshark
        icmpSocket.sendto(packet, (self.icmpAddress, 1))
        # 5. Record time of sending
        sentTime= time.time()
        return sentTime

    def recieveNodePing(icmpSocket):
        # 1. Wait for the socket to receive a reply- TTL = 0
        sentTime= time.time()
        ## Set the TTL for messages to 1 so they do not go past the local network segment
        #TTL = socket.recvmessage()
        
        TTL = struct.pack('b', 1)
        icmpSocket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, TTL)
        # 2. Once received, record time of receipt, otherwise, handle a timeout
        try:  # TTL == 0
            timeRecieved = time.time()
            # 3. Compare the time of receipt to time of sending, producing the total network delay- did when calculated RTT? 
            totalNetworkDelay = (timeRecieved * 1000) - sentTime
            # 4. Unpack the packet header for useful information, including the ID
            icmpType, icmpCode, icmpChecksum, icmpPacketID, icmpSeqNumber= struct.unpack("bbHHh", icmpHeader)
            # 5. Check that the ID matches between the request and reply and # 6. Return total network delay
            if(icmpPacketID == self.ID):
                return totalNetworkDelay
            else:
                return 0     
        
        except TTL != 0:  #if nothing is recieved, handle a timeout
            print("TTL is 0 - socket has not recieved a reply")
            return None
        
        
if __name__ == "__main__":
    args= setupArgumentParser()
    args.func(args)

def main():
    print("running")
    NetworkApplication()