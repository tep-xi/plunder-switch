import kinet
import random
import time

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
            print  (ratios[(step + idx*separation) % steps], .8, .9)
            fixture.hsv = (ratios[(step + idx*separation) % steps], .8, .9)
        print pds
        pds.go()
        time.sleep(pause)

# example of how to use the FadeIter
def fade_in(pds1):
    pds1.clear()
    pds2 = pds1.copy()
    div = 1.0 / len(pds)

    # every light comes up at a hue around the color wheel starting at base
    base = random.uniform(0, 1)
    for idx, fixture in enumerate(pds2):
        fixture.hsv = ((base + idx * div) / len(pds), 1, random.uniform(.5, 1))
    print "%s => %s" % (pds1, pds2)
    fi = kinet.FadeIter(pds1, pds2, 5)
    fi.go()

if __name__ == '__main__':
    # Our ethernet attached power supply.
    pds = kinet.PowerSupply("18.102.224.41")

    # Our light fixtures
    for i in range(0, 19, 3):
        # Attach our fixtures to the power supply
        pds.append(kinet.FixtureRGB(i))

    while True:
        fade_in(pds)
        epilepsy(pds, pause=.1, iterations=1)
        while True:
            rainbow_cycle(pds, pause=.2, steps=10000)
