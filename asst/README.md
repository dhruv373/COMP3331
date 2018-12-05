# COMP3331 Assignment Specs:

Refer to above pdf for more details.

# Aims:
On completing this assignment, you will gain sufficient expertise in the following skills: 

1. Detailed understanding of how reliable transport protocols such as TCP function. 

2. Socket programming for UDP transport protocol. 
3. Protocol and message design. 

# Overview 
As  part  of  this  assignment,  you  will  have  to  implement  Simple  Transport  Protocol  (STP),  a  piece  of 
software that consists of a sender and receiver component that allows reliable unidirectional data transfer. 
STP includes some of the features of the TCP protocols that are described 
in sections 3.5.3, 3.5.4 and 3.5.6 of the textbook (7th edition). You will use your STP protocol to transfer pdf files from the sender to the 
receiver.

You should implement STP as two separate programs: Sender and Receiver. You only have to 
implement unidirectional transfer of data from the Sender to the Receiver. As illustrated in Figure 1, data 
segments will flow from Sender to Receiver while ACK segments will flow from Receiver to Sender. 

Let us reiterate this, STP must be implemented on top of UDP. 
Do not use TCP sockets.
If you use TCP you will not receive any marks for your assignment. 
