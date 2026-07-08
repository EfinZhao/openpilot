#!/usr/bin/env python3

import cereal.messaging as messaging
import zmq
import json

context = zmq.Context()

# socket going to test_controller.py
socket_control = context.socket(zmq.PUSH)
socket_control.bind("tcp://*:5557")  # data source acts as the server


#laptop ip on router setup
# macbook ip on router setup: 192.168.10.227
# macbook ip on tethered setup: 192.168.43.56
# josh windows laptop ip on router setup: 192.168.10.226
# josh windows laptop ip on pixel: 10.254.198.60

"""
# ---- socket going to argonne app ------
socket_app = context.socket(zmq.PUSH)
socket_app.connect("tcp://192.168.10.226:5555")
# --------------------
"""

"""
js = messaging.SubMaster(['testJoystick'])
print("Listening for joystick messages... sending to port 5557")
"""
cs = messaging.SubMaster(['carState'])
print("Listening for carState messages...sending to port 5557")

while True:
    msg_list = [] # [throttle, speed]

    # Gather data from testJoystick topic
    """
    js.update()
    jsmsg = js['testJoystick']
    if jsmsg != ():
        axes = jsmsg.axes
        buttons = jsmsg.buttons
        throttle = axes[0]
        msg_list.append(throttle)
    """
    msg_list.append("throttle")

    #else:
        #print("No testJoystick message received.")

    # Gather data from carState topic
    cs.update()
    csmsg = cs['carState']
    if csmsg != ():
        speed = csmsg.vEgo
        msg_list.append(speed)
    else:
        print("No carState message received.")

        
    # Send throttle and speed to test_controller.py
    #print(f"Throttle: {axes[0]:.2f} | Speed: {speed:.2f} m/s")
    print(f"Speed: {speed:.2f} m/s")
    socket_control.send_json(msg_list)

    """""
    #  Send speed to argonne app
    socket_app.send(str(speed).encode())
    """
