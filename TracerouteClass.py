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
            x = x+1
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
        #sentTime = time.time() recieveTime?
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
        
