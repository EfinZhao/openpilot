<div align="center" style="text-align: center;">

<h1>openpilot</h1>

<p>
  <b>openpilot is an operating system for robotics.</b>
  <br>
  Currently, it upgrades the driver assistance system in 300+ supported cars.
  <br>
  This README explains how to properly use the ASL mod helper scripts
</p>

</div>

Using `asl_helper.py`
-----

`asl_helper.py` allows openpilot to recieve ASLs (Advisory Speed Limits), enabling autonomous following of the ASL.

To run `asl_helper.py`, you MUST provide it with the IP of the MQTT server that ASL messages are being posted to. The run command will look like this: `./asl_helper.py xxx.xxx.xxx.xxx`.

`asl_helper.py` has optional flags that allow you to adjust its behavior.
1. **`-i intersection_name` or `--intersection intersection_name`:** This runs `asl_helper.py` with a specified intersection to pull intersection minimum speeds from. If this flag is left unset, then `asl_helper.py` will default to using the intersection between Harvard and University.
2. **`--dry-run`:** This runs `asl_helper.py` in dry run mode, meaning that it will only print the ASL messages to the terminal, prevent actually sending the messages to openpilot. This is good for testing the reception of ASL messages in a safe way.
3. **`-v`** or **`--verbose`:** This runs `asl_helper.py` in verbose mode, allowing you to see detailed debug information.

`asl.toml` is the configuration file for `asl_helper.py` and contains the following settings:
1. The minimum speed for supported intersections and their straight approaches.

### How it works

`asl_helper.py` works by subscribing to the MQTT broker that contains the ASL messages published by the ASL client.

After recieving the ASL messages, `asl_helper.py` publishes the ASL as a cereal message under the `advisorySpeedLimit` service for openpilot to unpack and read.

If there exists a valid ASL under the `advisorySpeedLimit` service, then openpilot will use that speed as the cruise control speed. If not, then openpilot will fall back to using the cruise control speed found in the Car's `v_cruise_helper.v_cruise_kph` (see `openpilot/openpilot/selfdrive/car/card.py:161-200`).

