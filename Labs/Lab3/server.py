from socket import *
import sys

s = socket(AF_INET, SOCK_STREAM)
s.bind(('', int(sys.argv[1])))
print sys.argv[1]

s.listen(1); #queue defaults to 5

while True:
    client, addr = s.accept()
    print "Connected to ", addr
    try:
         data = client.recv(1024).decode(); #string from input (http request) contains filename
         print data
         name = data.split()[1][1:]
         print name
         file = open(name, "r").read()
         
         
         if "png" in name:
             client.send("HTTP/1.1 200 OK\nContent-Type: image/png\n\n")
             client.send(file)
         
         if "html" in name:
             client.send("HTTP/1.1 200 OK\nContent-Type: text/html\n\n")     
             client.send(file)
         
    
         client.send("\n")
    
    except IOError:
        client.send("HTTP/1.1 404 NOT_FOUND\n\n")    
        client.send("Connection: close\r\n")
        
    
    client.close()     
         
         


