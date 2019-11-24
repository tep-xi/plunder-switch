import time
import threading
import kinet
import random
import paho.mqtt.client as mqtt
import sys
import RPi.GPIO as GPIO
from subprocess import Popen

active = 0
# Our ethernet attached power supply.
pds = kinet.PowerSupply("18.102.224.41")

# Our light fixtures
for i in range(0, 19, 3):
    # Attach our fixtures to the power supply
    pds.append(kinet.FixtureRGB(i))

def dosomething(channel):
    global active
    active = GPIO.input(channel)

# caution to those with epilepsy
def epilepsy(pds, pause=.1, iterations=5, steps=50):
    # divide up the space of color between the lights
    div = steps / len(pds)
    # create an array of hue values by the step size
    ratios = map(lambda x: float(x)/steps, list(xrange(steps)))
    #shuffle it so we deterministically draw of of each color in a random order
    random.shuffle(ratios)
    for _ in range(iterations):
        for step in range(steps):
            if not active:
                break
            # for each fixture display it's color
            for idx, fixture in enumerate(pds):
                fixture.hsv = (ratios[(step + idx * div) % steps] , 1.0, 1.0)
            pds.go()
            time.sleep(pause)

# caution to those allergic to normies
def normalize(pds, pause=.1, iterations=5, steps=50):
    for idx, fixture in enumerate(pds):
        fixture.hsv = (0, 0, 0)
    pds.go()

def rainbow_cycle(pds, pause=.05, steps=1000, separation=10):
    div = steps / len(pds)
    ratios = map(lambda x: float(x)/steps, list(xrange(steps)))
    for step in range(steps, -1, -1):
        if not active:
            break
        ratio = 0
        for idx, fixture in enumerate(pds):
            fixture.hsv = (ratios[(step + idx*separation) % steps], 1, .9)
        pds.go()
        time.sleep(pause)

# example of how to use the FadeIter
def fade_in(pds1):
    pds1.clear()
    pds2 = pds1.copy()
    div = 1.0 / len(pds1)

    # every light comes up at a hue around the color wheel
    for idx, fixture in enumerate(pds2):
        fixture.hsv = (idx * div, 1, 1)
    pds = kinet.FadeIter(pds1, pds2, 10)
    pds.go()

GPIO.setmode(GPIO.BCM)
//3 should have a physical pull up resistor on it
GPIO.setup(3, GPIO.OUT)
GPIO.setup(12, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.add_event_detect(12, GPIO.BOTH, callback=dosomething)

ship = mqtt.Client()
print("PLUNDER BEFORE PILLAGE, MISSION FUFILLAGE! \nLAND HO!")
print("ATTEMPTIN' TO HAIL PIRATE-SHIP.MIT.EDU")
ship.loop_start()
ship.connect("PIRATE-SHIP.MIT.EDU")
# ship.loop_stop()
# ship.disconnect()
previous_mode = 0
while True:
    time.sleep(.5)
    print active
    if active:
        if not previous_mode:
            Popen(['play', 'siren.mp3'])
            ship.publish("plunder/cmnd/power", "0")
            fade_in(pds)
            epilepsy(pds, iterations=1)
            rainbow_cycle(pds, pause=.2, steps=100)
        previous_mode = 1
    else:
        if previous_mode:
            ship.publish("plunder/cmnd/power", "1")
            normalize(pds, pause=.2, steps=10000)
        previous_mode = 0
