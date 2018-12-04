import socket, select, pickle, os, glob, log_create, sys, time, datetime

INACTIVE       = 0
INIT           = 1
CONNECTED      = 2
TERMINATE      = 3

rcv_log = ""
#FOR LOGISTICS: RCV
file_size = 0
dataSz_ttl = 0
ttl_seg_rcv = 0
data_seg_rcv = 0
bitErr = 0
dup_data = 0
dup_acks =0

UDP_IP = "127.0.0.1"
currState = INACTIVE


global pkt_list
class Receiver:
    def __init__(self, rcv_host, rcv_port, rcv_filename):
        self.rcv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rcv_host = rcv_host
        self.rcv_port = rcv_port
        self.rcv_filename = rcv_filename
        self.rcv_buffer = ""
        self.rcv_start_time = time.time()
        self.rcv_state = INACTIVE
        self.rcv_ack = 0
        self.pkts_buffer = []
        self.pkts_rcv = []
        #number of bytes can be received by a socket in power of 2
    def get_pkts_rcv(self):
        return self.pkts_rcv

    def get_pkts_buffer(self):
        return self.pkts_buffer

    def set_rcv_ack(self, num):
        self.rcv_ack = num

    def get_rcv_ack(self):
        return self.rcv_ack

    def set_state(self,flag):
        self.rcv_state = flag

    def bind_socket(self):
        self.rcv_socket.bind((self.rcv_host, self.rcv_port))

    def get_state(self):
        return self.rcv_state

    def get_port(self):
        return self.rcv_port

    def get_sock(self):
        return self.rcv_socket

    def get_filename(self):
        return self.rcv_filename

    def set_start_time(self):
        self.rcv_start_time = time.time()

    def logging(self, host, event, pkt, data_sz):
        log_create.logging_rcv(rcv_log, host, event, pkt, data_sz)

    #this function send FINACK to sender
    def wrap_up(self,pkt, addr):

        new_pkt = log_create.pkt_gen()
        log_create.set_finack(new_pkt)
        data_str = pickle.dumps(new_pkt)
        self.rcv_socket.sendto(data_str, (addr[0], addr[1]))
        self.rcv_state = TERMINATE
        self.logging("receiver","snd", new_pkt, sys.getsizeof(pkt))


    def sendACK(self, pkt, addr):
        new_pkt = log_create.pkt_gen()
        log_create.set_ack(new_pkt)
        log_create.write_seq(new_pkt, log_create.get_seq(pkt))
        ack_num = log_create.get_seq(pkt) + len(log_create.extract_data(pkt))
        log_create.write_ack(new_pkt, ack_num)
        #print "................SENDING ACKS for pkt seq-num " + str(ack_num) + "......................\n"
        data_str = pickle.dumps(new_pkt)
        self.logging("receiver","snd", new_pkt, sys.getsizeof(pkt))
        self.rcv_socket.sendto(data_str, (addr[0], addr[1]))

    #sending acccumulated ACKs that cover prev uncked pkts
    def sendAccACK(self, ack_num, addr):
        new_pkt = log_create.pkt_gen()
        log_create.set_ack(new_pkt)
        #log_create.write_seq(new_pkt, log_create.get_seq(pkt))
        log_create.write_ack(new_pkt, ack_num)
        self.logging("receiver","snd", new_pkt, sys.getsizeof(new_pkt))
        #print "................SENDING ACKS for accumulated pkts " + str(ack_num) + "......................\n"
        data_str = pickle.dumps(new_pkt)
        self.rcv_socket.sendto(data_str, (addr[0], addr[1]))

    #extract SYNACK
    def rcv_SYNACK(self, pkt, addr):
        #let STP protocol sets seq & ack = 0 and only set flags for syn for a standard SYN Packet
        if(log_create.is_syn(pkt) and log_create.get_seq(pkt) == 0 and log_create.get_ack(pkt) == 0):
            #create a SYN ACK pkt back to sender after receiving self 1st handshake
            new_pkt = log_create.pkt_gen()
            log_create.set_synack(new_pkt)
            log_create.write_seq(new_pkt, 0)
            log_create.write_ack(new_pkt, 1)
            self.logging("receiver", "snd", new_pkt, sys.getsizeof(pkt))
            data_str = pickle.dumps(new_pkt)
            self.rcv_socket.sendto(data_str, (addr[0], addr[1]))
        else:\
            sys.exit("Invalid flags set in SYN packet received from 1st handshake\n")

def main():

    if(len(sys.argv) != 3):
        sys.exit("Usage error: python receiver.py <receiver_port> <file_r.pdf>");

    if((int(sys.argv[1]) < 1024) or (not sys.argv[1].isdigit())):
        sys.exit("receiver_port has to be a number > 1024");

    global rcv_log
    rcv_log = log_create.log_init_rcv(os.stat(sys.argv[2]).st_size)
    file_size = os.stat(sys.argv[2]).st_size
    #create a receiver obj and bind the rcv socket to the client host & port
    rcv = Receiver("localhost", int(sys.argv[1]), sys.argv[2]);
    rcv.bind_socket()
    newfile = rcv.get_filename()
    if(not os.path.exists(newfile)):
        fh = open(newfile, "wb")
    else:
        name = os.path.splitext(newfile)[0]
        timing = os.path.splitext(str(time.time()))[0]
        name += ("_" + timing +".pdf")
        fh = open( name , "wb")

    while True:
        #Receive data from the socket. return pair(string, address)
        #string is a string representing the data received and address is the address of the socket sending the data.
        ready = select.select([rcv.get_sock()], [], [], 3)
        if ready:
            data, addr = rcv.get_sock().recvfrom(1024)
            ls_data = pickle.loads(data)
            sz = sys.getsizeof(ls_data)
            global dataSz_ttl
            dataSz_ttl += sz

            global ttl_seg_rcv
            ttl_seg_rcv += 1


            #if a packet is received and the state is not active: SYN packet expected
            if(log_create.is_syn(ls_data) and rcv.get_state() == INACTIVE):
                #print "------------------------------------------------> RECEIVER INACTIVE\n"
                #start timer and logs
                rcv.logging("receiver", "rcv", ls_data, sz)

                rcv.set_start_time()
                rcv.rcv_SYNACK(ls_data, addr)
                rcv.set_state(INIT)
                #print "%.............first handshake established ---> SYNACK RESPONSE SENT\n"

            #packet received but SYNACK response already sent, ACK expected for conn established
            elif (log_create.is_ack(ls_data) and rcv.get_state() == INIT):
                rcv.set_state(CONNECTED)
                #print "%............third handshake established ---> CONNECTION ESTABLISHED!\n"

            elif (rcv.get_state() == CONNECTED):
                rcv.logging("receiver","rcv", ls_data, sys.getsizeof(ls_data))
                ##print str(log_create.valid_pkt(ls_data)) + "  BITERR? " + str(rcv.get_rcv_ack())
                if(log_create.valid_pkt(ls_data) < 0):
                    global bitErr
                    bitErr += 1
                    #print str(ls_data[2]) +" bitErr! " + str(hash("DATA"))

                #print "%-------------------------- DATA RECEIVED: " + str(log_create.get_seq(ls_data))

                if (log_create.is_data(ls_data)): #check if the packet data flag is set
                    buffer = log_create.extract_data(ls_data)

                    in_order = 0

                    #previous recorded rcv_ack must be the new pkt seq num
                    if(rcv.get_rcv_ack() == log_create.get_seq(ls_data)):
                        #print "rcv ack == seq"
                        in_order = 1
                    elif(rcv.get_rcv_ack() > log_create.get_seq(ls_data)):
                        #pkt received have been acked before
                        global dup_data
                        dup_data += 1

                    if(in_order == 1):

                        rcv.get_pkts_rcv().append(ls_data)

                        #print "DATA append:" + str(log_create.get_seq(ls_data)) + "  -> Expecting next seq num to be: " + str(log_create.get_seq(ls_data) + len(log_create.extract_data(ls_data))) +"...........................................\n"
                        fh.write(buffer)
                        #send back an ACK for this pkt
                        expected_ack = log_create.get_seq(ls_data) + len(log_create.extract_data(ls_data))
                        rcv.set_rcv_ack(expected_ack)
                        #print "Before: " + str(rcv.get_rcv_ack())

                        if(len(rcv.get_pkts_buffer()) > 0):
                            #if there are any pkts need buffering:
                            #   maybe due to dropped packets
                            #   will reach here when dropped pkts received again from retrans
                            remove = 0
                            index = -1
                            for p in rcv.get_pkts_buffer():
                                #print "In BUffer: " + str(log_create.get_seq(p)) + " " + str(len(log_create.extract_data(p)))
                                if(log_create.get_seq(p) <= rcv.get_rcv_ack()):
                                    #print "****write buffer to file after dropped pkt retransmitted! seq num: " + str(log_create.get_seq(p)) + "********\n"
                                    remove += 1
                                    buffer = log_create.extract_data(p) #append data in file
                                    fh.write(buffer)
                                    index = rcv.get_pkts_buffer().index(p)
                                    rcv.set_rcv_ack(log_create.get_seq(p) + len(log_create.extract_data(p)))
                                    #print "Need to remove: " + str(log_create.get_seq(p))

                            i = 0
                            while i < remove:
                                #print "RM pkts buffer until " + str(remove) + " "+ str(log_create.get_seq(rcv.get_pkts_buffer()[0]) ) + " " + str(len(log_create.extract_data(rcv.get_pkts_buffer()[0])))

                                rcv.get_pkts_buffer().pop(0)
                                i += 1

                            #for p in rcv.get_pkts_buffer():
                                #print "CHeck BUffer: index: " + str(rcv.get_pkts_buffer().index(p)) + " "+ str(log_create.get_seq(p)) + " " + str(len(log_create.extract_data(p)))

                            rcv.sendAccACK(rcv.get_rcv_ack(), addr)
                            #need to send accumulated ACKs of the latest segments
                        else: # if no packets dropped previously
                            rcv.sendACK(ls_data, addr)

                    else: #if in_order = 0

                        if(log_create.get_seq(ls_data) > rcv.get_rcv_ack()):
                            #need to keep acking prev recorded ack_num
                            #to trigger fast retrans

                            if(len(rcv.get_pkts_rcv()) > 0):
                                # for p in rcv.get_pkts_rcv():
                                #     last_rcv = p
                                pkt_exist = 0
                                for p in rcv.get_pkts_buffer():
                                    if(log_create.get_seq(p) == log_create.get_seq(ls_data)):
                                        pkt_exist = 1

                                if(pkt_exist == 0):
                                    rcv.get_pkts_buffer().append(ls_data)

                                    #print "RCV out of order: " + str(log_create.get_seq(ls_data)) + " -> Expected: " + str( rcv.get_rcv_ack()) + "...........................................\n"

                            else: #first pkt is dropped
                                 rcv.get_pkts_buffer().append(ls_data)
                                 #print "RCV out of order: " + str(log_create.get_seq(ls_data)) + " -> Expected: " + str( rcv.get_rcv_ack()) + "...........................................\n"
                        # dup acks sent to trigger fast retransmit
                        rcv.get_pkts_buffer().sort()
                        global dup_acks
                        dup_acks += 1

                        rcv.sendAccACK(rcv.get_rcv_ack(), addr)
                        global data_seg_rcv
                        data_seg_rcv += 1
                    #print "%............connection established ---> looping......\n"


                elif (log_create.is_fin(ls_data)):
                    fh.close()
                    rcv.wrap_up(ls_data, addr)
                    #print "%............connection established ---> TERMINATING CONNECTION......\n"
                    rcv.set_state(INACTIVE)
                    log_create.end_rcv_stats(rcv_log, file_size, ttl_seg_rcv, data_seg_rcv, bitErr, dup_data, dup_acks)
                    exit()




if __name__ == "__main__":
    main()
