import kinet
import random
import paho.mqtt.client as mqtt
import time
import sys

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
            # for each fixture display it's color
            for idx, fixture in enumerate(pds):
                fixture.hsv = (ratios[(step + idx * div) % steps] , 1.0, 1.0)
            pds.go()
            time.sleep(pause)

def rainbow_cycle(pds, pause=.05, steps=1000, separation=10):
    div = steps / len(pds)
    ratios = map(lambda x: float(x)/steps, list(xrange(steps)))
    for step in range(steps, -1, -1):
        ratio = 0
        for idx, fixture in enumerate(pds):
            fixture.hsv = (ratios[(step + idx*separation) % steps], .5, .9)
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

if __name__ == '__main__':
    print("PLUNDER BEFORE PILLAGE, MISSION FUFILLAGE! \nLAND HO!")

    ship = mqtt.Client()

    ship.is_connected = False
    print("ATTEMPTIN' TO HAIL PIRATE-SHIP.MIT.EDU")
    ship.loop_start()
    ship.connect("PIRATE-SHIP.MIT.EDU")

    ship.publish("plunder/cmnd/power", "0")

    ship.loop_stop()
    ship.disconnect()

    # Our ethernet attached power supply.
    pds = kinet.PowerSupply("18.102.224.41")

    # Our light fixtures
    for i in range(0, 19, 3):
        # Attach our fixtures to the power supply
        pds.append(kinet.FixtureRGB(i))

    fade_in(pds)
    epilepsy(pds, iterations=1)
    while True:
        rainbow_cycle(pds, pause=.2, steps=10000)
