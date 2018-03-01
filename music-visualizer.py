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
from aubio import tempo

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
frameDelay = 256
bufferQ = collections.deque(maxlen=frameDelay) # buffer of sound to delay music output
RATE = 48000
FRAMES = 2048
bpmQ = collections.deque(maxlen=4) # keeps track on the most likely bpm from the last few detections
beat_constant = 1
analyzation_time = 1
beat_delay = .001
#new idea, try a beat window and activate anything that is within the sliding window


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

def activateLights():
    while True:
        cur_time = time.time()
        delay_multiplier = (cur_time-analyzation_time) / beat_constant
        delay_multiplier = np.floor(delay_multiplier)
        delay =  beat_constant/8 - beat_delay
        print delay
        if delay < 0:
            continue
        else:
            time.sleep(delay)

        # display visualization of discretized signals
        shouldUpdate = False
        for idx, fixture in enumerate(pds):
            # shouldUpdate = shouldUpdate or (
            #     not fixture.rgb[0] == int(0xff * output[idx*3]) or
            #     not fixture.rgb[1] == int(0xff * output[idx*3+1]) or
            #     not fixture.rgb[2] == int(0xff * output[idx*3+2])
            # )
            # fixture.rgb = (output[idx*3],output[idx*3+1],output[idx*3+2])
            shouldUpdate = shouldUpdate or (
                not fixture.rgb[1] == int(0xff)
            )
            fixture.rgb = (1,.3,.3)
            # shouldUpdate = shouldUpdate or (
            #     not fixture.rgb[0] == int(0xff * max(output[idx*3],output[idx*3+1],output[idx*3+2]))
            # )
            # fixture.rgb = (max(output[idx*3],output[idx*3+1], output[idx*3+2]), .5, .5)
        if shouldUpdate:
            print 'updated'
            pds.go()

        time.sleep(.1)
        for idx, fixture in enumerate(pds):
            fixture.rgb = (.5,0,0)
        pds.go()

def computeFFT():
    global beat_constant
    global analyzation_time
    while True:
        time.sleep(0)
        # wait until there is enough data in the buffer to be processed
        if len(bufferQ) < frameDelay:
            time.sleep(1.5)
            continue
        try:
            # List of beats, in samples
            beats = []
            # Total number of frames read
            o = tempo("mkl", 256, 128, RATE)

            data = []
            # pass control to any other running threads
            time.sleep(0)
            # iterate over values from the buffer
            for i in range(0, frameDelay, 1):
                # time.sleep(0)
                rawData = bufferQ[i]
                for j in range(0, len(rawData), 4):
                    # time.sleep(0)
                    data.extend(struct.unpack('f', rawData[j:j+4]))
            # pass control to any other running threads
            time.sleep(0)

            beats = []
            is_beats = []
            for i in range(0, len(data), 128):
                # pass control to any other running threads
                time.sleep(0)
                is_beat= o(np.float32(data[i:i+128]))
                if is_beat:
                    this_beat = o.get_last_s()
                    beats.append(this_beat)
                    is_beats.append((i, is_beat))

            # if enough beats are found, convert to periods then to bpm
            if len(beats) > 1:
                time.sleep(0)
                if len(beats) < 4:
                    print("few beats found")
                bpms = 60./np.diff(beats)
                median_bpm = np.median(bpms)
                is_onset = np.int32(bpms) == np.int32(median_bpm)
                analyzation_time = time.time() # seconds
                onset_times = []
                for _,ons in enumerate(beats):
                    onset_times.append(ons)
                print 'the answer', median_bpm
                beat_equation = np.polyfit(range(len(onset_times)), onset_times, 1)
                beat_constant = np.polyval(beat_equation, 1)
            time.sleep(5)
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
            outp.get_buffer()[:] = bufferQ[4]
        else:
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
thread3 = Thread(target = activateLights)
thread3.start()
thread.join()

# When the above with-statement is left (either because the end of the
# code block is reached, or because an exception was raised inside),
# client.deactivate() and client.close() are called automatically.
