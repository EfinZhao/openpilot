#!/usr/bin/env python3

from cereal import messaging

import argparse
import json
import time
import paho.mqtt.client as mqtt


def parse():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "ip",
        help="IP of the MQTT server for openpilot to recieve ASL messages from"
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Enable dry run mode for safe testing'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose mode for debugging'
    )

    args = parser.parse_args()

    print(f"[i] Listening to {args.ip} for ASL messages...")

    if args.dry_run:
        print(f"[!] Dry run mode is on!")

    if args.verbose:
        print(f"[i] Verbose mode is on!")

    return args


class Messenger:
    def __init__(self, dry_run: bool = False):
        self.speed = 0
        self.dry_run = dry_run
        self.pm = messaging.PubMaster(['advisorySpeedLimit'])

    def publish_asl(self, speed: int):
        if speed is not None:
            self.speed = speed
        if self.dry_run:
            return

        msg = messaging.new_message('advisorySpeedLimit')
        msg.advisorySpeedLimit.speed = self.speed
        msg.valid = True
        msg.advisorySpeedLimit.valid = True
        self.pm.send('advisorySpeedLimit', msg)


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("[i] Connected succedssfully!")
        client.subscribe("asl/data")
    else:
        print(f"[!] Connection failed with code {rc}")


def on_message(client, userdata, msg: mqtt.MQTTMessage):
    messenger = userdata["messenger"]
    args      = userdata["args"]

    msg_str: str = msg.payload.decode('utf-8')

    if args.verbose:
        print(f"[i] Recieved: {msg_str}")

    msg_json: dict = json.loads(msg_str)
    if msg_json["in_range"]:
        try:
            for approach in msg_json["raw"]["approach_moves"]:
                if int(approach["approach"]) % 2 == 0:             # even approaches are straights, odd are left turn. We want straights!
                    asl: int = round(approach["asl"])
                    print(f"[i] ASL found! {asl}")
                    messenger.publish_asl(asl)
        except Exception as e:
            print(f"[!] ERROR: {e}")


def main():
    args = parse()

    MQTT_LISTEN_IP   = args.ip
    MQTT_LISTEN_PORT = 1883
    MQTT_KEEP_ALIVE  = 60

    if args.verbose:
        print(f"[i] {MQTT_LISTEN_IP=}")

    mqtt_args = {
        "messenger": None,
        "args": args
    }

    client = mqtt.Client(
        callback_api_version = mqtt.CallbackAPIVersion.VERSION2,
        userdata = mqtt_args
    )

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(f"{MQTT_LISTEN_IP}", MQTT_LISTEN_PORT, MQTT_KEEP_ALIVE)

    client.loop_start()

    messenger = Messenger(dry_run = args.dry_run)
    mqtt_args['messenger'] = messenger

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("[i] Stopping client...")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()

