import paho.mqtt.client as mqtt
import time
import sys

last_topic = ""
last_payload = ""

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("YARR, HAIL SUCCESSFUL")
        client.is_connected = True
    else:
        print("A BILGE RAT PLUNDERED THE CONNECTION! CHECK YER SETTINGS! Return code: " + str(rc))
        sys.exit(1)

def on_disconnect(client, userdata, flags, rc=0):
    print("PILLAGE BEFORE PLUNDER, WHAT A BLUNDER! \nPLUNDER BEFORE PILLAGE, MISSION FUFILLAGE! \nRETURNIN' TO THE SEVEN SEAS. Disconnect code: " + str(rc))

def on_message(coient, userdata, message):
    global last_topic, last_payload
    last_topic = message.topic
    last_payload = message.payload
    print("A MESSAGE IN A BOTTLE! \n topic: [" + last_topic + "] \n payload: [" + last_payload + "]")

broker = "PIRATE-SHIP.MIT.EDU"

ship = mqtt.Client()
ship.on_connect = on_connect
ship.on_message = on_message
ship.on_disconnect = on_disconnect

ship.is_connected = False
print("ATTEMPTIN' TO HAIL " + broker)
ship.loop_start()
ship.connect(broker)

time.sleep(5)

ship.subscribe("plunder/cmnd/power")
ship.publish("plunder/cmnd/power","1")

time.sleep(5)

ship.publish("plunder/cmnd/power", "0")

time.sleep(1)

ship.loop_stop()
ship.disconnect()
