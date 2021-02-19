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
   parser.set_defaults(hostname='lancaster.ac.uk')
   subparsers = parser.add_subparsers(help='sub-command help')
  
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
 
class WebServer(NetworkApplication):
 
   def handleRequest(tcpSocket):
       print("handleRequest starting")
       # 1. Receive request message from the client on connection (tcp?) socket
       #tcpSocket = serverSocket.accept() # acceptrequest
       #bufferSize = tcpSocket.CMSG_SPACE(4) # IPv4 address is 4 bytes in length - calculates the size of the buffer that should be allocated for receiving the ancillary data.
       #recieve message in buffer size allocated
       #requestMessage = tcpSocket.recvmsg(bufferSize[0, [0]])
       requestMessage = tcpSocket.recvmsg(1024)
       print("recieved message")
       # 2. Extract the path of the requested object from the message (second part of the HTTP header)
       #file = requestMessage.unpack_from(bufferSize)  # returns a tuple
       file = requestMessage.split()[1].partition("/")[2]
        #fileExist = "false"
        #filetouse = "/" + filename
       print("extract path")
       # 3. Read the corresponding file from disk
       print("read file from disk")
       
       # 4. Store in temporary buffer
       tempBuffer = socket.makefile( mode = 'r', buffering =None, encoding=None, errors=None, newline=None)
       tempFile = struct.pack_into(format, tempBuffer, 0, file)
       print("store in temp buffer")
       # 5. Send the correct HTTP response error
       httpResponseError= ("HTTP/1.1 404 Not Found\r\n")
       tcpSocket.sendmsg(httpResponseError)
       print("send error")
       # 6. Send the content of the file to the server?? socket
       tcpSocket.sendfile(file)
       #serverSocket.recvmsg(1024)
       print("send file")
       # 7. Close the connection socket
       print("socket closed")
       tcpSocket.close()
       pass
 
   def __init__(self, args):
       print('Web Server starting on port: %i...' % (args.port))
       # 1. Create server socket
       serverSocket= socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       #serverSocket = socket.create_server(socket.AF_INET, socket.SOCK_STREAM)
       #host = socket.gethostname()
       print("creating server socket")
       host = socket.gethostname()
       print ("hostname is: ", host)
       # 2. Bind the server socket to server address and server port
       serverAddress = (host, args.port)
       serverSocket.bind(serverAddress)
       #serverSocket.bind((sys.argv[1],80))
       print("binding socket to port: ", args.port)
       # 3. Continuously listen for connections to server socket
       serverSocket.listen(1)
       print("listening")
       # 4. When a connection is accepted, call handleRequest function, passing new connection socket (see https://docs.python.org/3/library/socket.html#socket.socket.accept)
       while True:
           try:
               newSocket, clientAddress = serverSocket.accept()
               print("accepting")
               handleRequest(newSocket)
               print("calling handleRequest")
               # 5. Close server socket
               serverSocket.close()
           except socket.timeout:
               continue
           break
 
 
class Proxy(NetworkApplication):
 
   def __init__(self, args):
       print('Web Proxy starting on port: %i...' % (args.port))
 
       #if __name__ == "__main__":
       #    args=setupArgumentParser()
       #    args.func(args)
          
       #1. create server socket and listen - connectionless socket: used to establish a TCP connection with the HTTP server
       serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
       #2. Bind the server socket to server address and server port
       #serverSocket.bind((socket.gethostname(), args.port))
       hostname = "127.0.0.1"
       serverAddress = (hostname, args.port) 
       serverSocket.bind(serverAddress)
       #serverSocket.bind((sys.argv[1],80))
       print("binding socket to", hostname, args.port)
       serverSocket.listen(5)
       print("listening")
       #4. Continuously listen for connections to server socket and proxy
       #5. When a connection is accepted, call handleRequest function, passing new connection socket  (?)
       while 1:
           print("accepting")
           connectionSocket, addr = serverSocket.accept() # accept TCP connection from client
           print("accepted xx")
           #with serverSocket.accept()[0] as connectionSocket: #pass new connection socket
           print("recieved connection from ", addr)
           #3. create proxy
           with connectionSocket:
               print("making proxy")
               proxySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
               #proxySocket.bind((hostname, (args.port+1))) #binding to another port
               proxySocket.connect((hostname, 8080))
               #proxySocket.bind(('', (args.port+1)))
               # # become a server socket
               #proxySocket.listen(5)
               #print("connectionSocket:", connectionSocket, "proxy: ", proxySocket, "serverSocket: ", serverSocket)
               # #handleRequest(proxySocket)
               print("calling handleRequest")
               self.handleRequest(connectionSocket, proxySocket, serverSocket, serverAddress)
               # 5. Close server socket?
               connectionSocket.close()
               break
               #serverSocket.close()
      
 
   def handleRequest(self, connectionSocket, proxySocket, serverSocket, serverAddress):
       #1. Receive request message from the client on connection socket
       # IPv4 address is 4 bytes in length
       #bufferSize = connectionSocket.CMSG_SPACE(4)
       bufferSize = 1024
       requestMessage = connectionSocket.recvmsg(bufferSize)
       #2. forward to proxy
       print("forwarding to proxy")
       print("request message: " ,requestMessage)
       #proxySocket.recvmsg(bufferSize) #doesn't like this 
       
       #3. proxy extracts the path of the requested object from the message (second part of the HTTP header)
       #file = struct.unpack_from(format, bufferSize, offset = 1)  # returns a tuple
       message = requestMessage[0]
       messageAsString = str(message)
       #filename = file.
       filename = messageAsString.split()[1].partition("/")[2]
       print("path:" ,filename)
       isObjectLocal = None #initialising
       #4. Read the corresponding file from disk: proxy server checks to see if object is stored locally
       try:
           isObjectLocal == True
           # 1.  if it does, the proxy server returns the object within a HTTP response message to the client browser
           httpResponse= ("GET/" + filename + " HTTP/1.1\r\n\r\n")
           print("print response:" ,httpResponse)
           # 3. Read the corresponding file from disk
           #change message from bytes to file so you can send it, open file in binary mode 
           messageAsFile = open(filename, 'wb')
           proxySocket.sendfile(messageAsFile, offset = 0, count=None)
           #close file 
           messageAsFile.close()
           #send via HTTP response message to client Browser
           proxySocket.sendto(httpResponse.encode(), serverAddress)
           #origin server recieves request
           #serverSocket.recv(httpResponse.encode())
           print("origin server recieved request")
           pass
       
       except IOError:
           if isObjectLocal == False:
               # 2.  if it doesn’t, the proxy server opens a TCP connection to the origin server
               originIP = serverSocket.gethostbyname(args.hostname)
               proxySocket.connect(originIP, args.port)
               # proxySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
               # bind the socket to a public host, and a well-known port
               # proxySocket.bind((socket.gethostname(), 80))
               #sends HTTP request for object
               httpRequest= ("GET /" + filename + " HTTP/1.1\r\n\r\n")
               proxySocket.send(httpRequest.encode())
               #origin server recieves request
               connectionSocket.recvmessage(httpRequest.encode())
          
               #5. Store in temporary buffer
               hostn = filename.split('/')[0].replace("www.","",1)
               connectionSocket.connect((hostn,80))
               # Create a temporary file on this socket
               tempObject = proxySocket.makefile('r', 0)
               tempObject.write("GET "+"http://" + filename + " HTTP/1.0\n\n")
  
               #6. Send the correct HTTP response error
               httpRequest= ("GET /" + filename + " HTTP/1.1\r\n\r\n")
               connectionSocket.send(httpRequest.encode())
               #connctionSocket.send("HTTP/1.1 200 OK\r\n\r\n")
               print("Request message sent")
               #7. send content to webserver
               object = connectionSocket.send(bufferSize[0, 0])
               #8. Send the content of the file to the socket
               serverSocket.recvmsg(object)
               #9. Close the connection socket 
               connectionSocket.close()
      
      
 
if __name__ == "__main__":
   args= setupArgumentParser()
   args.func(args)
 
def main():
   print("running")
   NetworkApplication()
