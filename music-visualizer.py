#!/usr/bin/env python3

"""Create a JACK client that takes input, does processing on it, then outputs it

"""
import sys
import traceback
import signal
import os
import jack
import threading
import numpy as np
from threading import Thread
import time
import collections
import pylab as pl
import struct
import itertools
import kinet
from scipy.signal import argrelextrema

# np.set_printoptions(threshold=np.nan)
if sys.version_info < (3, 0):
    # In Python 2.x, event.wait() cannot be interrupted with Ctrl+C.
    # Therefore, we disable the whole KeyboardInterrupt mechanism.
    # This will not close the JACK client properly, but at least we can
    # use Ctrl+C.
    signal.signal(signal.SIGINT, signal.SIG_DFL)
else:
    # If you use Python 3.x, everything is fine.
    pass

argv = iter(sys.argv)
# By default, use script name without extension as client name:
defaultclientname = os.path.splitext(os.path.basename(next(argv)))[0]
clientname = next(argv, defaultclientname)
servername = next(argv, None)
frameDelay = 16
bufferQ = collections.deque(maxlen=frameDelay) # buffer of sound to delay music output
RATE = 48000
ei = collections.deque(maxlen=43) # buffer for energy of sounds in beat detection

client = jack.Client(clientname, servername=servername)
if client.status.server_started:
    print('JACK server started')
if client.status.name_not_unique:
    print('unique name {0!r} assigned'.format(client.name))

# Our ethernet attached power supply.
pds = kinet.PowerSupply("18.102.224.64")
# Our light fixtures
fix1 = kinet.FixtureRGB(0)
fix2 = kinet.FixtureRGB(3)
# Attach our fixtures to the power supply
pds.append(fix1)
pds.append(fix2)

event = threading.Event()

def computeFFT():
    while True:
        time.sleep(0)
        # wait until there is enough data in the buffer to be processed
        if len(bufferQ) < frameDelay:
            time.sleep(1.5)
            continue
        try:
            # iterate over each of the speaker iinputs
            data = np.zeros(len(bufferQ[0])/4)
            # read the last four values from the buffer and add them to a list
            # for i in [-5,-3,-1]:
            for i in [0]:
                rawData = bufferQ[0]
                # pass control to any other running threads
                time.sleep(0)
                channelData = []
                for j in range(0, len(rawData), 4):
                    # pass control to any other running threads
                    time.sleep(0)
                    channelData.extend(struct.unpack('f', rawData[j:j+4]))
                data = np.add(data, channelData)
            #compute the difference for more accuracy
            # data = np.diff(data)

            # do fft
            #music is only in the range up to 2000 anyway
            fftdata = np.abs(np.fft.rfft(data))
            bin_distribution = np.geomspace(30, 1000, 64)
            # remove lower and higher frequencies, no beats happen there
            fftdata = fftdata[20:1000]

            # print 'fftdata', fftdata ,'fftdata end'
            maxFreqs= argrelextrema(fftdata, np.greater)
            # print 'maxfreak', maxFreqs
            # print 'actual val', fftdata[maxFreqs]
            # calculate the energy subbands
            digitized = np.digitize(range(len(fftdata)), bin_distribution)
            es = np.zeros(len(bin_distribution))
            for i in range(len(fftdata)):
                time.sleep(0)
                es[digitized[i]-1] += fftdata[i]
            # print es
            # add the energy subband to the buffer of past data
            ei.append(es)

            # find the average energy for each subbands
            avge = np.mean(ei, 0)

            beat = [0]*len(bin_distribution)
            for i in range(len(bin_distribution)):
                time.sleep(0)
                beat[i] = 1.0 if es[i] > 6*avge[i] else 0.0
                if es[i] > 4*avge[i] and es[i] <= 20*avge[i] and i<3:
                    print es[i], i, es[i]/avge[i]
            # print 'beat', beat
            #group into bins, one for each light
            bin_distribution = np.linspace(0, len(beat), 32)
            digitized = np.digitize(range(len(beat)), bin_distribution)
            output = [[] for i in range(len(bin_distribution)-1)]
            for i in range(len(beat)):
                time.sleep(0)
                output[digitized[i]-1].append(beat[i])
            # print 'output', output
            output = [np.mean(x) for x in output]
            # print 'fulll', output
            for i,x in enumerate(output):
                if x > .1:
                    output[i] = 1
                if x < .1:
                    output[i] = .1
            # print output
            # display visualization of discretized signals
            shouldUpdate = False
            for idx, fixture in enumerate(pds):
                shouldUpdate = shouldUpdate or (
                    not fixture.rgb[0] == int(0xff * output[idx*3]) or
                    not fixture.rgb[1] == int(0xff * output[idx*3+1]) or
                    not fixture.rgb[2] == int(0xff * output[idx*3+2])
                )
                fixture.rgb = (output[idx*3],output[idx*3+1],output[idx*3+2])
                # shouldUpdate = shouldUpdate or (
                #     not fixture.rgb[1] == int(0xff * output[idx*3+1])
                # )
                # fixture.rgb = (0,output[idx*3],0)
                # shouldUpdate = shouldUpdate or (
                #     not fixture.rgb[0] == int(0xff * max(output[idx*3],output[idx*3+1],output[idx*3+2]))
                # )
                # fixture.rgb = (max(output[idx*3],output[idx*3+1], output[idx*3+2]), .5, .5)
            if shouldUpdate:
                pds.go()

        except Exception, e:
            time.sleep(0)
            print 'error', str(e)
            _, _, traceback_ = sys.exc_info()
            print traceback.format_tb(traceback_)
            pass

@client.set_process_callback
def process(frames):
    assert len(client.inports) == len(client.outports)
    assert frames == client.blocksize
    for inp, outp in zip(client.inports, client.outports):
        bufferQ.append(bytes(inp.get_buffer()))
        if(len(bufferQ) >= frameDelay):
            outp.get_buffer()[:] = bufferQ[-1]

@client.set_shutdown_callback
def shutdown(status, reason):
    print('JACK shutdown!')
    print('status:', status)
    print('reason:', reason)
    event.set()

def processSound():
    ## create virtual ports for bridging between Jack's ports
    ## this creates a raw buffer in the inport until processing is finished and
    ## the result is sent to outports
    for number in 1, 2:
        client.inports.register("input_{0}".format(number))
        client.outports.register("output_{0}".format(number))

    with client:
        # When entering this with-statement, client.activate() is called.
        # This tells the JACK server that we are ready to roll.
        # Our process() callback will start running now.

        # Connect the ports.  You can't do this before the client is activated,
        # because we can't make connections to clients that aren't running.
        # Note the confusing (but necessary) orientation of the driver backend
        # ports: playback ports are "input" to the backend, and capture ports
        # are "output" from it.

        #  get the virtual ports for music source and sink
        print client.get_ports()
        pulseSource = client.get_ports('PulseAudio*')
        sonarSink = client.get_ports('Sonar')
        # do some plumbing
        if not pulseSource:
            raise RuntimeError('There was no source to read from')
        if not sonarSink:
            raise RuntimeError('Use alsa_out to setup the sound output')
        for src, dest in zip(pulseSource, client.inports):
            client.connect(src, dest)
        for src, dest in zip(client.outports, sonarSink):
            client.connect(src, dest)

        print('Press Ctrl+C to stop')
        try:
            event.wait()
        except KeyboardInterrupt:
            print('\nInterrupted by user')

thread = Thread(target = processSound)
thread.start()
thread2 = Thread(target = computeFFT)
thread2.start()
thread.join()

# When the above with-statement is left (either because the end of the
# code block is reached, or because an exception was raised inside),
# client.deactivate() and client.close() are called automatically.
