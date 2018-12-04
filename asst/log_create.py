#this file write to log files

#format
#<event> <time> <ack-number> <type-of-packet> <seq-number> <number-of-bytes-data>

#<event> = snd/rcv/drop/corr/dup/rord/dely/DA/RXT or a combination.

#corr = corrupted, dup = duplicated, rord=re-ordered,
# dely= delayed, DA=duplicate Acks received
# RXT= retransmission

#<type-of-packet> could be S (SYN), A (ACK), F (FIN) and D (Data)

import sys, os, glob, datetime, time, hashlib
import os.path

EVENT_SND = 0
EVENT_RCV = 1
EVENT_DROP = 2
EVENT_CORR = 3
EVENT_DUP = 4
EVENT_RORD = 5
EVENT_DELY = 6
EVENT_DA = 7
EVENT_RXT = 8

STATE_INIT = 1
STATE_CONNECTED = 2
STATE_FIN = 3

#indexes
SEQ = 0
ACK = 1
FLAG = 2
MSG = 3
CHSUM = 4

hr_min = ""
snd_log = ""
rcv_log = ""

def log_init_snd(file_sz):
    global hr_min
    if(hr_min == ""):
        hr_min = datetime.datetime.fromtimestamp(time.time()).strftime('%Hhr_%Mmin')
        hr_min += ("_" + datetime.datetime.today().strftime('%Y-%m-%d'))

    currTime = str(datetime.datetime.fromtimestamp(time.time()))
    #" + datetime.datetime.today().strftime('%Y-%m-%d')
    snd_log = "Sender_log_" +hr_min +".txt"
    file_size = file_sz

    try:
        logfile = open(snd_log,'w+')
        logfile.write("Sender log file for transmission at " + str(currTime) + "\n\n")
        logfile.write("<event> |          <time>            | <ack-number> | <type-of-packet> | <seq-number> | <number-of-bytes-data> |\n")
        logfile.write("--------|----------------------------|--------------|------------------|--------------|------------------------|\n")
        logfile.close()

    except:
        sys.exit("Log files failed to open");


    print "Writing to Sender_log.txt \n"

    return snd_log

def log_init_rcv(file_sz):
    global hr_min
    if(hr_min == ""):
        hr_min = datetime.datetime.fromtimestamp(time.time()).strftime('%Hhr_%Mmin')
        hr_min += ("_" + datetime.datetime.today().strftime('%Y-%m-%d'))
    file_size = file_sz
    currTime = str(datetime.datetime.fromtimestamp(time.time()))
    rcv_log = "Receiver_log_" + hr_min +".txt"

    try:
        logfile = open(rcv_log,'w+')
        logfile.write("Receiver log file for transmission at " + str(currTime) + "\n\n")
        logfile.write("<event> |          <time>            | <ack-number> | <type-of-packet> | <seq-number> | <number-of-bytes-data> |\n")
        logfile.write("--------|----------------------------|--------------|------------------|--------------|------------------------|\n")
        logfile.close()

    except:
        sys.exit("Log files failed to open");


    print "Writing to Receiver_log.txt \n"

    return rcv_log

def logging_snd(snd_log, host, event, pkt, data_sz):
    #pad the event type string with space
    stats = (event.ljust(8) + "| " + str(datetime.datetime.fromtimestamp(time.time())).ljust(27) +  "| " + str(get_ack(pkt)).ljust(13)
        +  "| " + str(type_of_pkt(pkt)).ljust(17) +  "| " + str(get_seq(pkt)).ljust(13) +  "| "
        + str(data_sz).ljust(23) + "| " + "\n")


    if(host == "sender"):
        try:
            #print "Logging.... -----> " + snd_log + "\n" + stats + "\n"
            fh = open(snd_log, 'a+')
            fh.write(stats)
            fh.close()

        except:
            sys.exit(snd_log + " failed to open");

    else:
        sys.exit("Please specify the host\n")

def logging_rcv(rcv_log, host, event, pkt, data_sz):
    #pad the event type string with space

    stats = (event.ljust(8) + "| " + str(datetime.datetime.fromtimestamp(time.time())).ljust(27) +  "| " + str(get_ack(pkt)).ljust(13)
        +  "| " + str(type_of_pkt(pkt)).ljust(17) +  "| " + str(get_seq(pkt)).ljust(13) +  "| "
        + str(data_sz).ljust(23) + "| " + "\n")


    if (host == "receiver"):
        try:
            #print "Logging.... -----> " + rcv_log + "\n" + stats + "\n"
            fh = open(rcv_log, 'a+')
            fh.write(stats)
            fh.close()

        except:
            sys.exit(rcv_log + " failed to open");

    else:
        sys.exit("Please specify the host\n")

def end_snd_stats(snd_log, file_size, ttl_seg_trans, pld_seg, drop_seg, corr_seg, reorder_seg, dup_seg, dely_seg, timeout_retrans, fast_retrans, dup_ack_rcv):
    stats = ("\n\n" + "***** !END OF TRANSMISSION! *****\n\n")
    stats += ("SENDER STATS: --------------------------------\n")
    stats += ("1. Size of the file (in Bytes): " + str(file_size) + "\n")
    stats += ("2. Segments transmitted (including drop & RXT): " + str(ttl_seg_trans) + "\n")
    stats += ("3. Number of Segments handled by PLD: " + str(pld_seg) + "\n")
    stats += ("4. Number of Segments Dropped: " + str(drop_seg) + "\n")
    stats += ("5. Number of Segments Corrupted: " + str(corr_seg) + "\n")
    stats += ("6. Number of Segments Re-ordered: " + str(reorder_seg) + "\n\n")
    stats += ("7. Number of Segments Duplicated: " + str(dup_seg) + "\n\n")
    stats += ("8. Number of Segments Delayed: " + str(dely_seg) + "\n\n")
    stats += ("9. Number of Retransmissions due to timeout: " + str(timeout_retrans) + "\n\n")
    stats += ("10. Number of Fast Retransmissions: " + str(fast_retrans) + "\n\n")
    stats += ("11. Number of Duplicate Acknowledgements received: " + str(dup_ack_rcv) + "\n\n")

    #print stats
    try:
        f = open(snd_log, 'a+')
        f.write(stats)
        f.close()
    except:
        sys.exit(snd_log + " failed to open for logistics purposes\n")

def end_rcv_stats(rcv_log, dataSz_ttl, ttl_seg_rcv, data_seg_rcv, bitErr, dup_data, dup_acks):
    stats = ("\n\n" + "***** !END OF TRANSMISSION! *****\n\n")
    stats += ("RECEIVER STATS: -------------------------------------\n")
    stats += ("1. Amount of Data Received (bytes): " + str(dataSz_ttl) + "\n")
    stats += ("2. Total segments received: " + str(ttl_seg_rcv) + "\n")
    stats += ("3. Data segments received: " + str(data_seg_rcv) + "\n")
    stats += ("4. Data Segments with bit errors: " + str(bitErr) + "\n")
    stats += ("5. Duplicate data segments received: " + str(dup_data) + "\n")
    stats += ("6. Duplicate Acks sent: " + str(dup_acks) + "\n\n")

    #print stats
    try:
        f = open(rcv_log, 'a+')
        f.write(stats)
        f.close()
    except:
        sys.exit(rcv_log + " failed to open for logistics purposes\n")


#pkt generate
def pkt_gen():
    pkt = [0, 0, 0, 0, 0, 0]
    return pkt

def write_seq(pkt, value):
    pkt[SEQ] = value
    return pkt

#store the ack value itself
def write_ack(pkt, value):
    pkt[ACK] = value
    return pkt

def get_seq(pkt):
    return pkt[SEQ]

def get_ack(pkt):
    return pkt[ACK]

def set_syn(pkt):
    pkt[FLAG] = hash("SYN")
    return pkt

def set_ack(pkt):
    pkt[FLAG] = hash("ACK")
    return pkt

def set_synack(pkt):
    pkt[FLAG] = hash("SYNACK")
    return pkt

def set_finack(pkt):
    pkt[FLAG] = hash("FINACK")
    return pkt

def set_fin(pkt):
   pkt[FLAG] = hash("FIN")
   return pkt

def set_data(pkt):
   pkt[FLAG] = hash("DATA")
   return pkt

def is_synack(pkt):

   if(pkt[FLAG] == hash("SYNACK")):
      return True
   return False

def is_finack(pkt):
   if(pkt[FLAG] == hash("FINACK")):
      return True
   return False

def is_syn(pkt):

   if(pkt[FLAG] == hash("SYN")):
      return True
   return False

def is_ack(pkt):
   if(pkt[FLAG] == hash("ACK")):
      return True
   return False

def is_fin(pkt):
   if(pkt[FLAG] == hash("FIN")):
      return True
   return False

def is_data(pkt):
   if(pkt[FLAG] == hash("DATA")):
      return True
   return False
#FLAG_SYN = 0b0001
#FLAG_ACK = 0b0010
#FLAG_FIN = 0b0100
#FLAG_DATA = 0b1000

def flip_bit(new_pkt):
    pkt = copy_pkt(new_pkt)

    #get the int in string of pkt's CHSUM
    print "hex_sum!!: " + pkt[CHSUM]
    int_sum = int(pkt[CHSUM], 32)
    int_sum = int_sum << 16
    pkt[CHSUM] = hex(int_sum)
    print "flipped hex_sum!!: " + pkt[CHSUM] + " original: " + new_pkt[CHSUM]
    return pkt



def valid_pkt(pkt):
    chsum = pkt[CHSUM]
    data = pkt[MSG]
    if(hashlib.md5(str(data)).hexdigest() != chsum):
        return -1
    return 1

def get_checksum():
    return pkt[CHSUM]

def type_of_pkt(pkt):
    flags = ""

    if (is_syn(pkt)):
      flags += "S"
    if (is_ack(pkt)):
      flags += "A"
    if (is_fin(pkt)):
      flags += "F"
    if (is_data(pkt)):
      flags += "D"
    if (is_synack(pkt)):
      flags += "SA"
    if (is_finack(pkt)):
        flags += "FA"

    return flags

def copy_data(pkt, message):
    pkt[MSG] = message
    res = hashlib.md5(message)
    hex_chsum = res.hexdigest()
    pkt[CHSUM] = hex_chsum
    return pkt

def copy_pkt(pkt):
    new_p = pkt_gen()
    new_p[SEQ] = pkt[SEQ]
    new_p[ACK] = pkt[ACK]
    new_p[FLAG] = pkt[FLAG]
    new_p[MSG] = pkt[MSG]
    new_p[CHSUM] = pkt[CHSUM]
    return new_p

def extract_data(pkt):
    return str(pkt[MSG])
