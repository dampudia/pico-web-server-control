"""
    Project: GurgleApps Webserver
    File: main.py
    Author: GurgleApps.com
    Date: 2021-04-01
    Description: Demonstrates how to use the GurgleApps Webserver
"""
from gurgleapps_webserver import GurgleAppsWebserver
import config
import utime as time
import uasyncio as asyncio
from machine import Pin
import ujson as json
from board import Board

BOARD_TYPE = Board().type
print("Board type: " + BOARD_TYPE)

if BOARD_TYPE == Board.BoardType.PICO_W:
    led = Pin("LED", Pin.OUT)
elif BOARD_TYPE == Board.BoardType.PICO:
    led = Pin(25, Pin.OUT)
elif BOARD_TYPE == Board.BoardType.ESP8266:
    led = Pin(2, Pin.OUT)
else:
    led = Pin(2, Pin.OUT)


blink_off_time = 0.5
blink_on_time = 0.5

status = True
shutdown = False

async def send_status(request, response):
    # send boolean status and number frequency
    response_string = json.dumps({"status": status})
    await response.send_json(response_string, 200)

async def main():
    global shutdown
    if config.BLINK_IP:
        await(server.blink_ip(led_pin = led, last_only = config.BLINK_LAST_ONLY))
    while not shutdown:
        if status:
            led.on()
            await asyncio.sleep(blink_on_time)
            led.off()
            await asyncio.sleep(blink_off_time)
        else:
            led.off()
            await asyncio.sleep(0.2)
            
server = GurgleAppsWebserver(config.WIFI_SSID, config.WIFI_PASSWORD, port=80, timeout=20, doc_root="/www", log_level=2)

server.add_function_route("/ping", send_status)


asyncio.run(server.start_server_with_background_task(main))
print('DONE')
