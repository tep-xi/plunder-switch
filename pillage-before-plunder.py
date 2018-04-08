import kinet
import random
import paho.mqtt.client as mqtt
import time
import sys

# caution to those allergic to normies
def normalize(pds, pause=.1, iterations=5, steps=50):
    for idx, fixture in enumerate(pds):
        fixture.hsv = (0, 0, .1)
    pds.go()


if __name__ == '__main__':
    print("PILLAGE BEFORE PLUNDER, WHAT A BLUNDER! \nRETURNIN' TO THE SEVEN SEAS")

    ship = mqtt.Client()

    ship.is_connected = False
    print("ATTEMPTIN' TO HAIL PIRATE-SHIP.MIT.EDU")
    ship.loop_start()
    ship.connect("PIRATE-SHIP.MIT.EDU")

    ship.publish("plunder/cmnd/power", "1")

    ship.loop_stop()
    ship.disconnect()

    # Our ethernet attached power supply.
    pds = kinet.PowerSupply("18.102.224.41")

    # Our light fixtures
    for i in range(0, 19, 3):
        # Attach our fixtures to the power supply
        pds.append(kinet.FixtureRGB(i))

    normalize(pds, pause=.2, steps=10000)
