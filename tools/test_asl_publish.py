#!/usr/bin/env python3
import time
import cereal.messaging as messaging


class ASLController:
    def __init__(self):
        self.speed = 0
        self.pm = messaging.PubMaster(['advisorySpeedLimit'])

    def _publish_asl_message(self):
        msg = messaging.new_message('advisorySpeedLimit')
        msg.advisorySpeedLimit.speed = self.speed
        msg.valid = True
        msg.advisorySpeedLimit.valid = True
        self.pm.send('advisorySpeedLimit', msg)
        print("[info] Sent advisorySpeedLimit =", self.speed)

    def _adjust_asl(self, amt: int):
        self.speed += amt

    def _set_asl(self, spd: int):
        self.speed = spd

    def _quit_test(self):
        print("[info] User requested test quit. Come to a stop safely!")
        exit()

def main():
    testASL = ASLController()

    testASL._publish_asl_message()

    INPUT_MAP = {
        '+' : lambda: testASL._adjust_asl(1),
        '++': lambda: testASL._adjust_asl(5),
        '-' : lambda: testASL._adjust_asl(-1),
        '--': lambda: testASL._adjust_asl(-5),
        'q' : lambda: testASL._quit_test(),
    }

    while True:
        # TODO: learn how to do input polling like the comma ai tunnel script and implement that here
        inpt: str = input("[info] Enter a command: ")
        try:
            inpt = int(inpt)
        except Exception as e:
            print(e)
        if inpt not in INPUT_MAP and not isinstance(inpt, int):
            print("[ERR!] command not found.")
            continue
        if isinstance(inpt, int):
            testASL._set_asl(inpt)
        else:
            INPUT_MAP[inpt]()
        testASL._publish_asl_message()

if __name__ == "__main__":
    main()
