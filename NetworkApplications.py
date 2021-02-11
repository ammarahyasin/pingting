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
            timeRecieved = time.time()
            information, address = icmpSocket.recvfrom(1024)
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
        icmpHeader=struct.pack("bbHHh", 8, 0, 0, ID, 1)

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
            nodalDelay = self.pingOneNode()
            self.printOneResult(ipAddress, 50, nodalDelay[1]*1000, 150)
            numberofNodes = numberofNodes + 1  # increments number of nodes
            # 4. Continue this process until stopped - until ICMP = 0
            if self.ICMP_CODE == 0:
                break
            # 3. Print out the returned delay (and other relevant details) using the printOneResult method
            # check this don't think its right
            self.printOneResult(ipAddress, 50, nodalDelay[1]*1000, 150)

    def pingOneNode():
        # 1. Create ICMP socket
        icmp_proto = socket.getprotobyname("icmp") #debugging
        icmpSocket= socket.socket(socket.AF_INET, socket.SOCK_RAW, icmp_proto)
        # 2. Call sendNodePing function
        timeSent= sendNodePing(icmpSocket, destinationAddress, 111)
        # 3. Call recieveNodePing function
        networkDelay= recieveNodePing(icmpSocket, destinationAddress, 111, 1000, timeSent)
         # 4. Close ICMP socket
        icmpSocket.close()
        # 5. Return total network delay- add up all the nodes
        for x in numberOfNodes:
            totalDelay = (networkDelay[x] + networkDelay[x + 1])
            if x == numberOfNodes:
                break
            return totalDelay

    def sendNodePing(icmpSocket):
         # 1. Build ICMP header
        icmpHeader= struct.pack("bbHHh", 8, 0, 0, ID, 1)
        # 2. Checksum ICMP packet using given function
        icmpChecksum= self.checksum(icmpHeader)
         # 3. Insert checksum into packet
        packetHeader= struct.pack("bbHHh", 8, 0, icmpChecksum, ID, 1)
        packet= packetHeader
        # 4. Send packet using socket
        # double check this //run with wireshark
        icmpSocket.sendto(packet, (destinationAddress, 1))
        # 5. Record time of sending
        sentTime= time.time()
        return sentTime

    def recieveNodePing():
        # 1. Wait for the socket to receive a reply- TTL = 0
        sentTime= time.time()
        TTL = recvmessage()
        # 2. Once received, record time of receipt, otherwise, handle a timeout
        try:  # TTL == 0
            timeRecieved = time.time()
            # 3. Compare the time of receipt to time of sending, producing the total network delay- did when calculated RTT? 
            totalNetworkDelay = (timeRecieved * 1000) - sentTime
            # 4. Unpack the packet header for useful information, including the ID
            icmpType, icmpCode, icmpChecksum, icmpPacketID, icmpSeqNumber= struct.unpack("bbHHh", icmpHeader)
            # 5. Check that the ID matches between the request and reply and # 6. Return total network delay
            if(icmpPacketID == ID):
                return totalNetworkDelay
            else:
                return 0     
        
        except TTL != 0:  #if nothing is recieved, handle a timeout
            print("TTL is 0 - socket has not recieved a reply")
            return None
        


class WebServer(NetworkApplication):

    def handleRequest(tcpSocket):
        # 1. Receive request message from the client on connection socket
        # IPv4 address is 4 bytes in length
        bufferSize = tcpSocket.CMSG_SPACE(4)
        requestMessage=tcpSocket.recvmsg(bufferSize[0, [0]])
        # 2. Extract the path of the requested object from the message (second part of the HTTP header)
        file=requestMessage.unpack_from( format, buffer, offset = 1)  # returns a tuple
        # 3. Read the corresponding file from disk
        socket.sendfile(file, offset = 0, count =None)
        # 4. Store in temporary buffer
        buffer = socket.makefile( mode = 'r', buffering =None, encoding=None, errors=None, newline=None)
        struct.pack_into(format, self.buffer, 0, file)
        # 5. Send the correct HTTP response error- what error is this abegggg
        httpResponseError= "GET /" + file + " HTTP/1.1\r\n\r\n"
        tcpSocket.sendmsg(httpResponseError)
        # 6. Send the content of the file to the socket
        tcpSocket.recvmsg(bufferSize[0, 0])
        # 7. Close the connection socket
        tcpSocket.close()
        pass

    def __init__(self, args):
        print('Web Server starting on port: %i...' % (args.port))
        # 1. Create server socket
        serverSocket= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print("creating server socket")
        # 2. Bind the server socket to server address and server port
        serverSocket.bind((socket.gethostname(), 80))
        print("binding socket")
        # 3. Continuously listen for connections to server socket
        serverSocket.listen(5)
        # 4. When a connection is accepted, call handleRequest function, passing new connection socket (see https://docs.python.org/3/library/socket.html#socket.socket.accept)
        newSocket= socket.accept()
        while True:
            handleRequest(newSocket)
            print("calling handleRequest")
            # 5. Close server socket
            serverSocket.close()


class Proxy(NetworkApplication):

    def __init__(self, args):
        print('Web Proxy starting on port: %i...' % (args.port))

        if __name__ == "__main__":
            args=setupArgumentParser()
            args.func(args)

        # 1. browser establishes TCP connection to proxy server-- SERVER CREATES SOCKET AND LISTENS
        # connectionless socket: used to establish a TCP connection with the HTTP server.
        serverSocket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverSocket.listen(5)
        #1.1. CLIENT CREATES SOCKET
        # create server socket
        # create an INET, STREAMing socket
        #filename = sys.argv[1:]
        clientSocket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # bind the socket to a public host, and a well-known port
        clientSocket.bind((socket.gethostname(), 80))
        # become a server socket
        clientSocket.listen(5)
        # 4. When a connection is accepted, call handleRequest function, passing new connection socket (see https://docs.python.org/3/library/socket.html#socket.socket.accept)
        while 1:
            clientSocket, addr=serverSocket.accept()
            print("recieved connection from ", addr)
            handleRequest(clientSocket)
            print("calling handleRequest")
            # 5. Close server socket? or both sockets?
            serverSocket.close()

    def handleRequest(clientSocket):
        # 1. Receive request message from the client on connection socket
         # IPv4 address is 4 bytes in length
        bufferSize= clientSocket.CMSG_SPACE(4)
        requestMessage= clientSocket.recvmsg(bufferSize[0, [0]])
        # 2. Extract the path of the requested object from the message (second part of the HTTP header)
        file= requestMessage.unpack_from( format, buffer, offset = 1)  # returns a tuple

         # 2. send HTTP request for object to proxy server
        httpRequest= "GET /" + file + " HTTP/1.1\r\n\r\n"
        clientSocket.send(httpRequest.encode())
        print("Request message sent.")
        # 3. proxy server checks to see if copy of object is stored locally- calls class localObject
        localObject(requestMessage)
        # 4. proxy server sends HTTP request for the object into the cache-to-server TCP connection

        # 5. origin server receives request

        # 6. origin server sends object to proxy server within a HTTP response

        # 7. proxy server receives the object
        object= serverSocket.recvmsg(bufferSize[0, 0])

        # 8. proxy server stores copy in its local storage

        # 9. proxy server sends copy -in HTTP response message- to client browser over TCP connection

        # proxy server checks to see if copy of object is stored locally
    def localObject(requestMessage):
        filename= requestMessage.split()[1]
        try:
            isObjectLocal=open(filename[1:], "r")  # open file in text mode
            isObjectLocal="true"
            # 1.  if it does, the proxy server returns the object within a HTTP response message to the client browser
            # 3. Read the corresponding file from disk
            socket.sendfile(object, offset = 0, count =None)
            #send via HTTP response message to client Browser

        except isObjectLocal == "false":
            # 2.  if it doesn’t, the proxy server opens a TCP connection to the origin server:
            proxySocket=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # bind the socket to a public host, and a well-known port
            proxySocket.bind((socket.gethostname(), 80))
            #sends HTTP request for object

            #origin server recieves request
            clientServer.recvmessage()

if __name__ == "__main__":
    args= setupArgumentParser()
    args.func(args)

def main():
    print("running")
    NetworkApplication()
