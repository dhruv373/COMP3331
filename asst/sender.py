import sys, os, time, log_create, socket, random, pickle, select, signal
from time_calc import *
from threading import Timer


INACTIVE       = 0
INIT           = 1
CONNECTED      = 2
FIN_WAIT_1     = 3

snd_log = ""
#FOR LOGISTICS: SND
file_size = 0
ttl_seg_trans = 0
pld_seg = 0
drop_seg = 0
corr_seg = 0
reorder_seg = 0
dup_seg = 0
dely_seg = 0
timeout_retrans = 0

fast_retrans = 0
dup_acks = 0
order = 0

sentTime_ms = 0
rcvTime_ms = 0
SampleRTT = 0
timeout = 0
prevEstRTT = 0
prevDevRTT = 0

def main():

    if(len(sys.argv) != 15):
        sys.exit("Usage Error: python sender.py receiver_host_ip receiver_port file.pdf MWS MSS gamma pDrop pDuplicate pCorrupt pOrder maxOrder pDelay maxDelay seed\n")

    if ((int(sys.argv[2]) <= 1024) or (not sys.argv[2].isdigit())):
        sys.exit("Args Error: port specify must be larger than 1024\n")

    if (not os.path.isfile(sys.argv[3])):
        sys.exit("Args Error: file not in current directory\n")

    rcv_host = sys.argv[1]
    rcv_port = int(sys.argv[2])
    snd_filename = sys.argv[3]
    mws = int(sys.argv[4])
    mss = int(sys.argv[5])
    gamma = int(sys.argv[6])
    pDrop = float(sys.argv[7])
    pDup = float(sys.argv[8])
    pCorr = float(sys.argv[9])
    pOrder = float(sys.argv[10])
    maxOrder = int(sys.argv[11])
    pDely = float(sys.argv[12])
    maxDely = int(sys.argv[13])
    seed = int(sys.argv[14])
    snd = Sender(rcv_host, rcv_port, snd_filename, mws, mss, gamma, pDrop, pDup, pCorr, pOrder, maxOrder, pDely, maxDely, seed)

    global snd_log
    snd_log = log_create.log_init_snd(os.stat(sys.argv[3]).st_size)

    file_size = os.stat(sys.argv[3]).st_size


    #1. initiate hanshake
    if(snd.get_state() == INACTIVE):
        snd.init_handshake()
        global sentTime_ms
        sentTime_ms = time.time()

        ##print "%............initiated handshake ---> SYN PACKET SENT!\n"

    if(snd.get_state() == INIT):
        #2. try catch block to treat the timeout as a exception
        try:
            data, addr = snd.get_sock().recvfrom(1024)
            ls_data = pickle.loads(data)
            snd.logging("sender","rcv", ls_data, sys.getsizeof(ls_data))
            snd.extract_SYNACK(ls_data)
            global rcvTime_ms
            rcvTime_ms = time.time()


            ##print "%............SYNACK pkt received ---> ACK RESPONSE SENT!\n"


        except socket.timeout:
            sys.exit("*************  CONNECTION TIMED OUT  ********************\n")

    if(snd.get_state() == CONNECTED):

        global timeout
        #init_EstRTT = 500
        #init_DevRTT = 250
        timeout = TimeoutInterval(rcvTime_ms , sentTime_ms, 500, 250, gamma)
        snd.get_sock().settimeout(timeout/1000)
        #start sending file in segments
        finished = snd.file_transfer()

        if(finished):
            #initiate end conn after finished trans
            snd.set_state(FIN_WAIT_1)
            fin_pkt = log_create.pkt_gen()
            log_create.set_fin(fin_pkt)
            log_create.write_ack(fin_pkt, 0)
            log_create.write_seq(fin_pkt, 0)
            data_str = pickle.dumps(fin_pkt)

            snd.get_sock().sendto(data_str, (snd.get_host(), snd.get_port()))
            ##print "%............FIN pkt sent, initiate TERMINATION........\n"
            snd.logging("sender", "snd", fin_pkt, sys.getsizeof(fin_pkt))

            if(snd.get_state() != INACTIVE):
                #should receive one ACK pkt and one FIN from rcv
                try:
                    while(not data or not log_create.is_finack(ls_data)):
                        data, addr = snd.get_sock().recvfrom(1024)
                        ls_data = pickle.loads(data)
                        snd.logging("sender", "rcv", ls_data, sys.getsizeof(ls_data))
                        ##print log_create.type_of_pkt(ls_data) + "!!!!!!!"
                        if(log_create.is_finack(ls_data)):
                            ack_pkt = log_create.pkt_gen()
                            log_create.set_ack(ack_pkt)
                            log_create.write_ack(ack_pkt, 0)
                            log_create.write_seq(ack_pkt, 0)
                            data_str = pickle.dumps(ack_pkt)

                            snd.get_sock().sendto(data_str, (snd.get_host(), snd.get_port()))
                            snd.logging("sender", "snd", ack_pkt, sys.getsizeof(ack_pkt))
                            snd.set_state(INACTIVE)
                            ##print "%............ACK pkt sent to comfirm TERMINATING........\n"
                except socket.timeout:
                    sys.exit("*************  CONNECTION TIMED OUT  ********************\n")

        log_create.end_snd_stats(snd_log, file_size, ttl_seg_trans, pld_seg, drop_seg, corr_seg, reorder_seg, dup_seg, dely_seg, timeout_retrans, fast_retrans, dup_acks)
        ##print "*************  FILE TRANSMISSION SUCCESS!  ********************\n"

def get_file(filename):
    try:
        ##print 'tryin to open ' + filename + "\n"
        fh = open(filename, "r")
        filedata = fh.read()
        fh.close()

    except:
        sys.exit("CANT FIND FILENAME REQUESTED \n")

        return filedata

def sendDely(rcv, pkt, rxt_flag):
    global ttl_seg_trans
    global dely_seg
    ##print "pDelay: now send packet... " + str(time.time())
    data_str = pickle.dumps(pkt)
    expected_ack = log_create.get_seq(pkt) + len(log_create.extract_data(pkt))
    rcv.get_send_Time()[expected_ack] = time.time()
    rcv.get_sock().sendto(data_str, (rcv.get_host(), rcv.get_port()))

    exist = 0
    if(rxt_flag == 0):
        for a in rcv.get_pkts_on_fly():
            if(log_create.get_seq(a) == log_create.get_seq(pkt)):
                exist = 1
        if(exist == 0 ):
            rcv.get_pkts_on_fly().append(pkt)
    dely_seg += 1
    ttl_seg_trans += 1

class Sender:
    def __init__(self, rcv_host, rcv_port, snd_filename, mws, mss, gamma, pDrop, pDup, pCorr, pOrder, maxOrder, pDely, maxDely, seed):
        self.snd_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rcv_host = rcv_host
        self.rcv_port = rcv_port
        self.snd_filename = snd_filename
        self.mws = (mws/mss)
        self.mss = mss
        self.gamma = gamma
        self.pDrop = pDrop
        self.pDup = pDup
        self.pCorr = pCorr
        self.pOrder = pOrder
        self.maxOrder = maxOrder
        self.pDely = pDely
        self.maxDely = maxDely
        self.seed = random.seed(seed)
        self.snd_time = time.time()
        self.snd_state = INACTIVE
        self.curr_ack = 0
        self.curr_seq = 0
        self.pkts_on_fly = []
        self.acked_num = {}
        self.pkts_acked = []
        self.pkts_waiting= []
        self.pkts_rord = []
        self.rord = 0
        self.send_Time = {}
        self.recv_Time = {}

    def get_send_Time(self):
        return self.send_Time

    def get_pkts_on_fly(self):
        return self.pkts_on_fly

    def set_curr_ack(self, num):
        self.curr_ack = num

    def file_transfer(self):
        #form a queue of packets divided by mss
        ##print "--------------------------------FILE TRANS---------------------------------\n"
        sock = self.snd_socket
        f = open(self.snd_filename, "rb")
        data = f.read(self.mss)
        next_segment = 0
        while(data):
            p = log_create.pkt_gen()
            log_create.write_seq(p, next_segment)
            log_create.copy_data(p, data)
            #set the message in pkt
            log_create.set_data(p)
            #set flag that this is a data pkt

            self.pkts_waiting.append(p)
            data = f.read(self.mss)
            next_segment += self.mss

        f.close()

        ##print str(len(self.pkts_waiting)) + " pkts to go, sz each:" + str(self.mss)
        ttl_pkts_trans = len(self.pkts_waiting)

        global order

        while(len(self.pkts_waiting) > 0 or len(self.pkts_on_fly) > 1):
            ##print str(len(self.pkts_waiting)) + " -----> " + str(len(self.pkts_on_fly))
            while(len(self.pkts_waiting) > 0 and len(self.pkts_on_fly) < self.mws):
                ##print "-----------------------------------------------------------------------------------------\n"
                ##print "whyd stop?? " + str(len(self.pkts_on_fly)) + " " + str(len(self.pkts_waiting)) + " " + str(len(self.pkts_acked))

                ##print str(order) + " currently..."
                if(len(self.pkts_rord) > 0 and order == 0):
                    #if there is a pkt waiting for reorder
                    #and countdown == 0
                    p = self.pkts_rord.pop(0)
                    data_str = pickle.dumps(p)
                    self.pkts_on_fly.append(p)
                    self.pkts_on_fly.sort()


                    ##print "reorder pkt !: " + str(log_create.get_seq(p)) + " buff sz: " + str(len(log_create.extract_data(p))) + "\n"
                    expected_ack = log_create.get_seq(p) + len(log_create.extract_data(p))
                    self.send_Time[expected_ack] = time.time()
                    sock.sendto(data_str, (self.rcv_host, self.rcv_port))

                else:

                    to_be_sent = self.pkts_waiting.pop(0)
                    ##print "pkt going into pld!: " + str(log_create.get_seq(to_be_sent)) + " buff sz: " + str(len(log_create.extract_data(to_be_sent))) + "\n"

                    self.pld_handler(to_be_sent, 0)



                ##print "-----------------------------------------------------------------------------------------\n"

            global timeout

            ##print "-----------------------------------RECV ACKS----------------------------------------\n"
            #for p in self.pkts_on_fly:
                ##print "seq num pkt on fly:  " + str(log_create.get_seq(p))


            try:
                response, addr = self.snd_socket.recvfrom(1024)
                data_arr = pickle.loads(response)

                global SampleRTT
                global prevEstRTT
                global prevDevRTT

                if(log_create.is_ack(data_arr)):
                    ##print "HELLLOOOOOOOO " + str(log_create.get_ack(data_arr)) + " " +str(self.curr_ack)
                    if(log_create.get_ack(data_arr) >= self.curr_ack):
                        self.set_curr_ack(log_create.get_ack(data_arr))
                        ##print "ACK NUM RECV: " + str(log_create.get_ack(data_arr))
                        index = 0
                        #need to remove pkts acked frm list of pkts on fly
                        self.pkts_on_fly.sort()
                        for p in self.pkts_on_fly:
                            #if p in list seq_num + len of data = received ack
                            ack = log_create.get_ack(data_arr)
                            ##print str((log_create.get_seq(p) + len(log_create.extract_data(p)))) + " and " +str(ack) +"!!!!!!!!!!!!"
                            if((log_create.get_seq(p) + len(log_create.extract_data(p))) <= ack):
                                ##print "need to remove pkts on fly with seq num: " + str(log_create.get_seq(p))

                                self.pkts_acked.append(p)
                                self.recv_Time[ack] = time.time()

                                if(ack in self.send_Time): # if there was a previously recorded time
                                    SampleRTT = getTimediff(self.recv_Time[ack]  , self.send_Time[ack])
                                    newEstRTT = EstRTTcalc( prevEstRTT, SampleRTT)
                                    prevEstRTT = newEstRTT
                                    newDevRTT = DevRTTcalc(prevDevRTT, SampleRTT, prevEstRTT)
                                    prevDevRTT = newDevRTT
                                    new_timeout = TimeoutInterval(self.recv_Time[ack], self.send_Time[ack], prevEstRTT, prevDevRTT, self.gamma)
                                    timeout = new_timeout
                                    #update timeout interval from sampled RTT

                                #index = self.pkts_on_fly.index(p)
                                index += 1


                        i = 0
                        while i < index:
                            ##print "RM pkts on fly: " + str(index) + " "+ str(log_create.get_seq(self.pkts_on_fly[0]) )

                            self.pkts_on_fly.pop(0)
                            i += 1

                        #if no p in pkts on fly list matched with ths acked
                        # possibly a dup ack
                        #at the same time increment the occurence of such ack_num
                        ack_num =log_create.get_ack(data_arr)
                        if(ack_num in self.acked_num):
                            global fast_retrans
                            global dup_acks
                            self.acked_num[ack_num] += 1
                            #if the occurence > 3, Acknowledging the one missing
                            if(self.acked_num[ack_num] >= 3):
                                is_rord = 0 #to check whether
                                #this RXT is for a rord pkt??
                                for p in self.pkts_rord:
                                    if(ack_num == log_create.get_seq(p)):
                                        is_rord = 1
                                        self.acked_num[ack_num] = 0
                                        ##print "occurence of ack num RORD: " + str(log_create.get_seq(p)) + " " + str(p[2]) + " missing Sender!!!"
                                        fast_retrans += 1

                                 
                                        dup_acks += 1
                                        self.pld_handler(p, 1)
                                        break

                                if(is_rord == 0):
                                    for p in self.pkts_on_fly:
                                        ###print "FOUND: " + str(log_create.get_seq(p))
                                        if(log_create.get_seq(p) == ack_num):
                                            self.acked_num[ack_num] = 0
                                            ##print "occurence of ack num: " + str(log_create.get_seq(p)) + " " + str(p[2]) + " missing Sender!!!"
                                            fast_retrans += 1

                                            
                                            dup_acks += 1
                                            self.pld_handler(p, 1)
                                            break

                                    for p in self.pkts_acked:
                                        ###print "FOUND: " + str(log_create.get_seq(p))
                                        if(log_create.get_seq(p) == ack_num):
                                            self.acked_num[ack_num] = 0
                                            ##print "occurence of ack num: in acked?? " + str(log_create.get_seq(p)) + " " + str(p[2]) + " missing Sender!!!"
                                            fast_retrans += 1

                                           
                                            dup_acks += 1
                                            self.pld_handler(p, 1)
                                            break

                        else:
                            ##print "increment occur of : " + str(ack_num)
                            self.acked_num[ack_num] = 1
                ##print "------------------------------------!!!!!!!!!!!!!!!--------------------------------------\n"
            except socket.timeout:
                self.retrans()
            # except:
            #     ##print "helpppppppp"
            #

                ###print "FINALLLLstop?? " + str(len(self.pkts_on_fly)) + " " + str(len(self.pkts_waiting)) + " " + str(len(self.pkts_acked)) + " " + str(ttl_seg_trans)
        if(len(self.pkts_waiting) == 0):
            return 1
        else:
            return 0

    def retrans(self):
        ##print "---------------------------------SOCKET TIMEOUT-------------------------------\n"
        global timeout_retrans

        #need to retrans all current packets on fly
        i=0
        length = len(self.pkts_on_fly)
        ##print str(length) + "\n"
        while (i < len(self.pkts_on_fly)):
            #data_str = pickle.dumps(p)
            ###print "in" + str(self.pkts_on_fly[i])
            ##print "Socket time out sent : " + str(log_create.get_seq(self.pkts_on_fly[i]))
            self.pld_handler(self.pkts_on_fly[i], 1)
            timeout_retrans += 1
            ###print "out\n"
            #sock.sendto(data_str, (self.rcv_host, self.rcv_port))
            #time.sleep(0.05)#(TimeoutInterval/1000))
            i += 1


    def pld_handler(self,pkt, rxt_flag):
        random.seed(self.seed)
        random_num = random.random()
        code = 0
        global ttl_seg_trans
        global pld_seg
        global dup_seg
        global drop_seg
        global corr_seg
        global order
        global reorder_seg
        ttl_seg_trans += 1
        pld_seg += 1
        if(random_num < self.pDrop):
            #If the chosen number is less than pDrop, drop the STP segment.
            #only logs abt the lost pkt
            #expecting ACKs from rcv
            ##print str(random_num) + " < pDrop: dropping packet "+ str(log_create.get_seq(pkt)) + " " + str(len(log_create.extract_data(pkt))) +".................\n"
            self.logging("sender", "drop", pkt, sys.getsizeof(pkt))
            #although dropped, sender is unaware so it is append to pkts_on_fly
            exist = 0
            if(rxt_flag == 0):
                for a in self.pkts_on_fly:
                    if(log_create.get_seq(a) == log_create.get_seq(pkt)):
                        exist = 1
                if(exist == 0 ):
                    self.pkts_on_fly.append(pkt)
            self.pkts_on_fly.sort()
            drop_seg += 1

        else:
            random_num = random.random()

            if(random_num < self.pDup):
                dup_seg += 1
                #create identical pkt and add to head of unsent pkts list
                p = log_create.copy_pkt(pkt)
                self.pkts_waiting.insert(0, p)
                ##print str(random_num) + " < pDup: duplicate packet "+ str(log_create.get_seq(pkt)) + " " + str(len(log_create.extract_data(pkt))) +".................\n"
                #send the original pkt nonetheless
                exist = 0
                if(rxt_flag == 0):
                    for a in self.pkts_on_fly:
                        if(log_create.get_seq(a) == log_create.get_seq(pkt)):
                            exist = 1
                    if(exist == 0 ):
                        self.pkts_on_fly.append(pkt)
                self.pkts_on_fly.sort()
                data_str = pickle.dumps(pkt)
                expected_ack = log_create.get_seq(pkt) + len(log_create.extract_data(pkt))
                self.send_Time[expected_ack] = time.time()
                self.snd_socket.sendto(data_str, (self.rcv_host, self.rcv_port))


                if(order > 0):
                    order -= 1

            else:
                random_num = random.random()
                if(random_num < self.pCorr):
                    corr_seg += 1
                    #record the pkt before corrupting it
                    exist = 0
                    if(rxt_flag == 0):
                        for a in self.pkts_on_fly:
                            if(log_create.get_seq(a) == log_create.get_seq(pkt)):
                                exist = 1
                        if(exist == 0 ):
                            self.pkts_on_fly.append(pkt)
                    self.pkts_on_fly.sort()
                    #flip the bit of pkt seq_num
                    np = log_create.flip_bit(pkt)
                    ##print str(random_num) + " < pCorr: corrupt packet "+ str(log_create.get_seq(np)) + " " + str(len(log_create.extract_data(np))) +".................\n"
                    self.logging("sender", "corr", np, sys.getsizeof(np))
                    data_str = pickle.dumps(np)
                    #send corrupted pkt to rcv
                    expected_ack = log_create.get_seq(np) + len(log_create.extract_data(np))
                    self.send_Time[expected_ack] = time.time()
                    self.snd_socket.sendto(data_str, (self.rcv_host, self.rcv_port))


                    if(order > 0):
                        order -= 1

                else:
                    random_num = random.random()
                    if(random_num < self.pOrder):

                        #if there is no pkt waiting for reordering
                        if(len(self.pkts_rord) <= 0 and len(self.pkts_waiting) > self.maxOrder):
                            reorder_seg += 1
                            #simply stick the pkt back rord list

                            order = self.maxOrder
                            self.pkts_rord.append(pkt)
                            ##print str(random_num) + " < pOrder: reorder packet "+ str(log_create.get_seq(pkt)) + " " + str(len(log_create.extract_data(pkt))) +".................\n"

                            #forward the rest of "maxOrder" pkts
                            p = self.pkts_waiting.pop(0)
                            exist = 0
                            if(rxt_flag == 0):
                                for a in self.pkts_on_fly:
                                    if(log_create.get_seq(a) == log_create.get_seq(p)):
                                        exist = 1
                                if(exist == 0 ):
                                    self.pkts_on_fly.append(p)

                            self.pkts_on_fly.sort()
                            self.logging("sender", "rord", p, sys.getsizeof(p))
                            ##print str(random_num) + " < pOrder: sending packet "+ str(log_create.get_seq(p)) + " " + str(len(log_create.extract_data(p))) +".................\n"
                            data_str = pickle.dumps(p)
                            expected_ack = log_create.get_seq(p) + len(log_create.extract_data(p))
                            self.send_Time[expected_ack] = time.time()
                            self.snd_socket.sendto(data_str, (self.rcv_host, self.rcv_port))



                        else:
                            ##print "JUST SENDING..............."
                            #forward the STP segment to UDP
                            data_str = pickle.dumps(pkt)
                            ##print "send seq_num: " + str(log_create.get_seq(pkt)) + " buff sz: " + str(len(log_create.extract_data(pkt))) + "\n"
                            expected_ack = log_create.get_seq(pkt) + len(log_create.extract_data(pkt))
                            self.send_Time[expected_ack] = time.time()
                            self.snd_socket.sendto(data_str, (self.rcv_host, self.rcv_port))

                            exist = 0
                            if(rxt_flag == 0):
                                for a in self.pkts_on_fly:
                                    if(log_create.get_seq(a) == log_create.get_seq(pkt)):
                                        exist = 1
                                if(exist == 0 ):
                                    self.pkts_on_fly.append(pkt)
                            self.pkts_on_fly.sort()

                            self.logging("sender", "snd", pkt, sys.getsizeof(pkt))
                            if(order > 0):
                                order -= 1
                    else:
                        random_num = random.random()

                        if(random_num < self.pDely):
                            random.seed(self.maxDely)
                            dely = random.random()
                            t = Timer(dely, sendDely, (self, pkt, rxt_flag))

                            ##print str(random_num) + " < " + str(self.pDely) + " pDelay: delay packet "+ str(dely) + " ms " + str(log_create.get_seq(pkt)) + " " + str(len(log_create.extract_data(pkt))) +".................\n"
                            ##print "currTime:  " + str(time.time())
                            self.logging("sender", "snd", pkt, sys.getsizeof(pkt))
                            if( not t.isAlive()):
                                t.start()

                        else:
                            ##print "JUST SENDING..............."
                            #forward the STP segment to UDP
                            data_str = pickle.dumps(pkt)
                            ##print "send seq_num: " + str(log_create.get_seq(pkt)) + " buff sz: " + str(len(log_create.extract_data(pkt))) + "\n"
                            expected_ack = log_create.get_seq(pkt) + len(log_create.extract_data(pkt))
                            self.send_Time[expected_ack] = time.time()
                            self.snd_socket.sendto(data_str, (self.rcv_host, self.rcv_port))

                            exist = 0
                            if(rxt_flag == 0):
                                for a in self.pkts_on_fly:
                                    if(log_create.get_seq(a) == log_create.get_seq(pkt)):
                                        exist = 1
                                if(exist == 0 ):
                                    self.pkts_on_fly.append(pkt)
                            self.pkts_on_fly.sort()

                            self.logging("sender", "snd", pkt, sys.getsizeof(pkt))
                            if(order > 0):
                                order -= 1
        return code



    def extract_SYNACK(self, pkt):
        if(log_create.is_synack(pkt) and (log_create.get_seq(pkt) == 0) and (log_create.get_ack(pkt) == 1)):
            new_pkt = log_create.pkt_gen()
            log_create.set_ack(new_pkt)
            log_create.write_seq(new_pkt, 1)
            log_create.write_ack(new_pkt, 1)
            curr_ack = 1
            curr_seq = 1
            data_str = pickle.dumps(new_pkt)
            expected_ack = log_create.get_seq(new_pkt) + len(log_create.extract_data(new_pkt))
            self.send_Time[expected_ack] = time.time()
            self.snd_socket.sendto(data_str, (self.rcv_host, self.rcv_port))
            self.logging("sender", "snd", new_pkt, sys.getsizeof(new_pkt))
            self.set_state(CONNECTED)
        else:
            sys.exit("Invalid flags while extracting SYNACK pkt\n")

    def get_sock(self):
        return self.snd_socket

    def logging(self, host, event, pkt, data_sz):
        log_create.logging_snd(snd_log, host, event, pkt, data_sz)

    def init_handshake(self):
        if(self.snd_state == INACTIVE):
            new_pkt = log_create.pkt_gen()
            log_create.set_syn(new_pkt)
            data_str = pickle.dumps(new_pkt)
            expected_ack = log_create.get_seq(new_pkt) + len(log_create.extract_data(new_pkt))
            self.send_Time[expected_ack] = time.time()
            self.snd_socket.sendto(data_str, (self.rcv_host, self.rcv_port))
            self.logging("sender", "snd", new_pkt, sys.getsizeof(new_pkt))
            self.set_state(INIT)
        else:
            sys.exit("Handshake attempted while state is alrdy active\n")



    def set_state(self,flag):
        self.snd_state = flag

    def get_host(self):
        return self.rcv_host

    def get_port(self):
        return self.rcv_port

    def get_mws(self):
        return self.mws

    def get_mss(self):
        return self.mss

    def get_gamma(self):
        return self.gamma

    def get_pDely(self):
        return self.pDely

    def get_maxDely(self):
        return self.maxDely

    def get_snd_time():
        return self.get_snd_time

    def get_state(self):
        return self.snd_state

    def get_maxOrder(self):
        return self.maxOrder

    def get_pOrder(self):
        return self.pOrder

    def get_pCorr(self):
        return self.pCorr

    def get_pDrop(self):
        return self.pDrop

    def get_pDup(self):
        return self.pDup

    def get_seed(self):
        return self.seed

    def get_host(self):
        return self.rcv_host

    def get_port(self):
        return self.rcv_port

if __name__ == "__main__":
    main()
