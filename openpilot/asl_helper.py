#!/usr/bin/env python3

from cereal import messaging

import argparse
import json
import time
import threading
import paho.mqtt.client as mqtt

RED    = '\033[31m'
GREEN  = '\033[32m'
YELLOW = '\033[33m'
BLUE   = '\033[34m'
RESET  = '\033[0m'

ASL_TIMEOUT = 5.0


# ================================================================================================ #


connection_failed = threading.Event()


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

    print(f"[.] Listening to {args.ip} for ASL messages...")

    if args.dry_run:
        print(f"{YELLOW}[!] Dry run mode is on!{RESET}")

    if args.verbose:
        print(f"{BLUE}[i] Verbose mode is on!{RESET}")

    return args


class Messenger:
    def __init__(self, dry_run: bool = False):
        self.speed = 0
        self.dry_run = dry_run
        self.pm = None if dry_run else messaging.PubMaster(['advisorySpeedLimit'])
        self.last_asl_time = time.monotonic()

    def publish_asl(self, speed: int) -> None:
        self.last_asl_time = time.monotonic()
        if speed is not None:
            self.speed = speed
        if self.dry_run:
            return

        msg = messaging.new_message('advisorySpeedLimit')
        msg.advisorySpeedLimit.speed = self.speed
        msg.valid = True
        msg.advisorySpeedLimit.valid = True
        self.pm.send('advisorySpeedLimit', msg)

    def publish_asl_lost(self) -> None:
        if self.dry_run:
            return
        msg = messaging.new_message('advisorySpeedLimit')
        msg.advisorySpeedLimit.speed = 0
        msg.valid = False
        msg.advisorySpeedLimit.valid = False
        self.pm.send('advisorySpeedLimit', msg)


def on_connect(client, userdata, flags, rc, properties=None):
    if rc.is_failure:
        print(f"{YELLOW}[!] Connection failed: {rc}{RESET}")
        connection_failed.set()
    else:
        print(f"{BLUE}[i] Connected succedssfully!{RESET}")
        client.subscribe("asl/data")


def on_message(client, userdata, msg: mqtt.MQTTMessage):
    messenger = userdata["messenger"]
    args      = userdata["args"]

    try:
        msg_str: str = msg.payload.decode('utf-8')
        if args.verbose:
            print(f"[.] Recieved: {msg_str}")
        msg_json: dict = json.loads(msg_str)
        in_range = msg_json["in_range"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError) as e:
        print(f"{YELLOW}[!] Bad payload, skipping: {e}{RESET}")

    if not in_range:
        return

    try:
        for approach in msg_json["raw"]["approach_moves"]:
            if int(approach["approach"]) % 2 == 0:             # even approaches are straights, odd are left turn. We want straights!
                asl: int = round(approach["asl"])
                print(f"[.] ASL Found! {asl}")
                asl = max(asl, 35)                             # TODO: The minimum ASL speed should be determined by the approach we are on
                print(f"{BLUE}[i] Publishing: {asl}{RESET}")
                messenger.publish_asl(asl)
    except (KeyError, ValueError, TypeError) as e:
        print(f"{YELLOW}[!] Bad approach entry, skipping: {e}{RESET}")


def main():
    args = parse()

    MQTT_LISTEN_IP   = args.ip
    MQTT_LISTEN_PORT = 1883
    MQTT_KEEP_ALIVE  = 60

    if args.verbose:
        print(f"[.] {MQTT_LISTEN_IP=}")

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

    messenger = Messenger(dry_run = args.dry_run)

    mqtt_args['messenger'] = messenger

    try:
        client.connect(f"{MQTT_LISTEN_IP}", MQTT_LISTEN_PORT, MQTT_KEEP_ALIVE)
        client.loop_start()
    except (OSError, ConnectionError) as e:
        print(f"{RED}[!] Could not connect to {MQTT_LISTEN_IP}! {e}{RESET}")
        raise SystemExit(1)

    asl_lost = False

    try:
        while True:
            elapsed = time.monotonic() - messenger.last_asl_time
            if elapsed > ASL_TIMEOUT:
                if not asl_lost:
                    asl_lost = True
                    print(f"{YELLOW} No ASL found for {ASL_TIMEOUT}s! Chill mode disengaging now!{RESET}")
                messenger.publish_asl_lost()
            else:
                asl_lost
            if connection_failed.is_set():
                print(f"{RED}[!] Network loop died! Exiting!{RESET}")
                raise SystemExit(1)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"{BLUE}[i] Stopping client...{RESET}")
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()

