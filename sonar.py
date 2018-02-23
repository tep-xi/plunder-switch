#!/usr/bin/env python3

"""Create a JACK client that takes input, does processing on it, then outputs it

"""
import sys
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
bufferQ = collections.deque()
frameDelay = 8
RATE = 44100

client = jack.Client(clientname, servername=servername)
if client.status.server_started:
    print('JACK server started')
if client.status.name_not_unique:
    print('unique name {0!r} assigned'.format(client.name))

event = threading.Event()

def computeFFT():
    while True:
        # wait until there is enough data in the buffer to be processed
        if len(bufferQ) < 5:
            time.sleep(1.5)
            continue
        try:
            # iterate over each of the speaker iinputs
            for inp in client.inports:
                data = []
                # read the last four values from the buffer and add them to a list
                for i in [-5,-3,-1]:
                    # pass control to any other running threads
                    time.sleep(0)
                    for j in range(0, len(bufferQ[i]), 4):
                        # pass control to any other running threads
                        time.sleep(0)
                        data.extend(struct.unpack('f', bufferQ[i][j:j+4]))

                # do fft
                fftdata = np.abs(np.fft.rfft(data))
                # get list of frequencies in the range supported by the sample rate
                bins = np.linspace(0, RATE/2, len(fftdata))
                # prune out values above 2000Hz (they won't be in any decent music anyway)
                # prune out fft values less than some threshold, they're just noise anyway
                for i in range(len(bins)):
                    time.sleep(0)
                    if bins[i] > 2000:
                        bins = bins[:i]
                        max_value = max(fftdata[:i])
                        for i in range(len(fftdata)):
                            if (fftdata[i] < (.2*max_value)):
                                fftdata[i] = 0
                        break
                #  average over intervals of 200 bins
                num_means = np.linspace(0, bins[-1], 200)
                digitized = np.digitize(bins, num_means).tolist()
                bin_means = []
                groups = enumerate(digitized)
                groups = itertools.groupby(groups, key=lambda x: x[1])
                for _, g in groups:
                    time.sleep(0)
                    g = list(g)
                    # print g
                    bin_means.append(np.mean([fftdata[k] for k,_ in g]))
                # discretize the signal by taking the max of the averages over 9 bins
                num_maxs = np.linspace(0, bins[-1], 9)
                digitized = np.digitize(num_means, num_maxs).tolist()
                bin_maxs = [0]*len(num_maxs)
                for i in range(len(num_means)):
                    time.sleep(0)
                    maxs = max(bin_means[i], bin_maxs[digitized[i]-1])
                    bin_maxs[digitized[i]-1] = maxs

                # display visualization of discretized signals
                pl.clf()
                pl.xlim(-200, num_means[-1])
                pl.ylim(0, 100)
                time.sleep(0)
                pl.bar(num_maxs, bin_maxs, width=20)
                pl.grid(True)
                pl.draw()
        except Exception, e:
            print 'error', str(e)
            pass

@client.set_process_callback
def process(frames):
    assert len(client.inports) == len(client.outports)
    assert frames == client.blocksize
    for inp, outp in zip(client.inports, client.outports):
        bufferQ.append(bytes(inp.get_buffer()))
        if(len(bufferQ) > frameDelay):
            outp.get_buffer()[:] = bufferQ.popleft()


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
# thread.join()
pl.xlabel("Frequency(Hz)")
pl.ylabel("Power(dB)")
# matplotlib must be started in the main thread
pl.show()

# When the above with-statement is left (either because the end of the
# code block is reached, or because an exception was raised inside),
# client.deactivate() and client.close() are called automatically.
