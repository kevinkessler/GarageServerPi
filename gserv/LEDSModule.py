'''
LED Control Module for Garage Server
Copyright (C) 2018 Kevin Kessler

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
from gserv.BaseModule import BaseModule
from gserv.led_patterns.Spin import SpinPattern
from gserv.led_patterns.Solid import SolidPattern
from gserv.led_patterns.Countdown import CountdownPattern
from rpi_ws281x import Adafruit_NeoPixel
import logging
import sys

'''
Module to control 8 WS2812B LEDs. Uses the SPI pin to send out the timing based signal to
control the LEDs. Receives the display pattern command through MQTT, and deligates the
actual pattern generation to classes which create the list of grb data for each of the 8
leds (ws2812b's expect the color data in grb order, not rgb order)
'''


class LedsModule(BaseModule):

  def __init__(self, config_file, secure_file):
    BaseModule.__init__(self, config_file, secure_file)

    try:
      self.neopixel_pin = self.config['neopixel_pin']
    except KeyError as e:
      logger = logging.getLogger(__name__)
      err = "Key error in LEDS Init: {}".format(e)
      logger.error(err)
      self.mqtt_client.publish('gserv/error', err)
      sys.exit(2)

    self.pattern_classes = {
      "BLANK": SolidPattern,
      "GREEN_CLOCKWISE": SpinPattern,
      "GREEN_COUNTERCLOCKWISE": SpinPattern,
      "RED_CLOCKWISE": SpinPattern,
      "RED_COUNTERCLOCKWISE": SpinPattern,
      "BLUE_CLOCKWISE": SpinPattern,
      "BLUE_COUNTERCLOCKWISE": SpinPattern,
      "CYAN_CLOCKWISE": SpinPattern,
      "CYAN_COUNTERCLOCKWISE": SpinPattern,
      "COUNTDOWN": CountdownPattern
    }

    self.current_pattern = None

  def run(self):
    self.strip = Adafruit_NeoPixel(8, self.neopixel_pin, 800000, 10, False, 255, 0)
    self.strip.begin()
    self.change_pattern("BLANK")
    self.mqtt_client.loop_forever()

  def change_pattern(self, pattern_name):
    if self.current_pattern is not None:
      self.current_pattern.stop()

    if pattern_name in self.pattern_classes:
      self.current_pattern = self.pattern_classes[pattern_name](self, pattern_name, self.config)
      self.current_pattern.start()
    else:
      self.current_pattern = None

  def on_message(self, client, userdata, message):
    logger = logging.getLogger(__name__)
    msg = message.payload.decode('utf-8')
    logger.debug(msg)
    self.change_pattern(msg)

  def writeSPIData(self, ledList):
    led_index = 0
    for l in ledList:
      self.strip.setPixelColorRGB(led_index, l[1], l[0], l[2])
      led_index += 1

    self.strip.show()


def main():
  ledsMod = LedsModule('config/leds.yaml', 'config/secure.yaml')
  logger = logging.getLogger(__name__)
  logger.info("LedsModule starting")
  ledsMod.run()


if __name__ == "__main__":
  main()
