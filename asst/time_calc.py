import sys, os, glob, datetime, time, math
import os.path

def getTimeStr():
    str_time = datetime.strptime(datetime.datetime.time(datetime.datetime.now()), '%H:%M:%S')
    return str_time

def getTimediff(rcvTime_ms , sentTime_ms):
    rtt_in_ms = round(rcvTime_ms - sentTime_ms, 3)
    return rtt_in_ms

#EstimatedRTT = 500 milliseconds and DevRTT = 250 milliseconds.
#----SampleRTT----
#the moment sent -> the moment ack for it is received
#new value every RTT

    '''need to set the formula!
        (TimeoutInterval = EstimatedRTT + 4 * DevRTT)
        EstimatedRTT = 0.875 * EstimatedRTT + 0.125 * SampleRTT
        DevRTT = (1-0.25) * DevRTT + 0.25 * | SampleRTT - EstimatedRTT|

        Use the initial value of EstimatedRTT = 500 milliseconds and DevRTT = 250 milliseconds.
    '''

def EstRTTcalc( prevEstRTT, SampleRTT):
    return ((0.85 * prevEstRTT) + (0.125 * SampleRTT))

def DevRTTcalc(prevDevRTT, SampleRTT, EstRTT):
    diff = SampleRTT - EstRTT
    return ((0.75 * prevDevRTT) + (0.25 * abs(diff)))

def TimeoutInterval(rcvTime_ms , sentTime_ms, prevEstRTT, prevDevRTT, gamma):
    SampleRTT = getTimediff(rcvTime_ms , sentTime_ms)
    EstRTT = EstRTTcalc(prevEstRTT , SampleRTT)
    DevRTT = DevRTTcalc(prevDevRTT, SampleRTT, EstRTT)

    return (EstRTT + (gamma * DevRTT))

#needs to be calculated in this order
#because the values calculated in the previous formula
#is used in the next
