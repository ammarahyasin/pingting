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

    parser_w = subparsers.add_parser(
        'web', aliases=['w'], help='run web server')
    parser_w.set_defaults(port=8080)
    parser_w.add_argument('port', type=int, nargs='?',
                          help='port number to start web server listening on')
    parser_w.set_defaults(func=WebServer)

    parser_x = subparsers.add_parser(
        'proxy', aliases=['x'], help='run proxy')
    parser_x.set_defaults(port=8000)
    parser_x.add_argument('port', type=int, nargs='?',
                          help='port number to start web server listening on')
    parser_x.set_defaults(func=Proxy)

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

    def receiveOnePing(self, icmpSocket, destinationAddress, ID, timeout):

        # 1. Wait for the socket to receive a reply. #2. Once received, record time of receipt, otherwise, handle a timeout
        try:
            information, address = icmpSocket.recvfrom(1024)
            timeRecieved = time.time()
            timeSent = information.split()[2]
            
            # 3. Compare the time of receipt to time of sending, producing the total network delay
            timeSent= self.sendOnePing(icmpSocket, destinationAddress, 111)
            totalNetworkDelay = (timeRecieved*1000) - timeSent
            
            # 4. Unpack the packet header for useful information, including the ID
            icmpType, icmpCode, icmpChecksum, icmpPacketID, icmpSeqNumber = struct.unpack("bbHHh", icmpHeader)

            # 5. Check that the ID matches between the request and reply AND THEN 6. Return total network delay
            if(icmpPacketID == self.ID):
                return totalNetworkDelay

            else:
                return 0

        except timeout: # No response received, print the timeout message
            print("Request timed out")



    def sendOnePing(self, icmpSocket, destinationAddress, ID):
        # 1. Build ICMP header
        icmpHeader=struct.pack("bbHHh", 8, 0, 0, ID, 1) #8 = type code, 0s= deafault, 1= base sequence number

        # 2. Checksum ICMP packet using given function
        icmpChecksum = self.checksum(icmpHeader)

        # 3. Insert checksum into packet
        icmpHeader = struct.pack("bbHHh", 8, 0, icmpChecksum, ID, 1)

        # 4. Send packet using socket- double check this //run with wireshark
        icmpSocket.sendto(icmpHeader, (destinationAddress, 1))
        
        # 5. Record time of sending
        timeSent=time.time()
        return timeSent

    def doOnePing(self, destinationAddress, timeout):
        # 1. Create ICMP socket
        # Translate an Internet protocol name (for example, 'icmp') to a constant suitable for passing as the (optional) third argument to the socket() function.
        icmp_proto = socket.getprotobyname("icmp") #debugging
        icmpSocket = socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp_proto)
        #icmpSocket = socket.socket(socket.AF_INET,socket.SOCK_RAW, socket.IPPROTO_ICMP)

        # 2. Call sendOnePing function
        timeSent = self.sendOnePing(icmpSocket, destinationAddress, 111)

        # 3. Call receiveOnePing function
        networkDelay = self.receiveOnePing(icmpSocket, destinationAddress, 111, 1000, timeSent)

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
            debuggingTimeout = args.timeout
            print("testing:", ipAddress, debuggingTimeout)
            returnedDelay = self.doOnePing(ipAddress, debuggingTimeout)
            # 3. Print out the returned delay (and other relevant details) using the printOneResult method
            self.printOneResult(ipAddress, 50, returnedDelay, 150)
            #Example use of printOneResult - complete as appropriate
            # 4. Continue this process until stopped - did this through the while True