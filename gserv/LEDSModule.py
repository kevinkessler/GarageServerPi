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
import wiringpi
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
      self.spi_port = self.config['spi_port']
    except KeyError as e:
      logger = logging.getLogger(__name__)
      err = "Key error in LEDS Init: {}".format(e)
      logger.error(err)
      self.mqtt_client.publish('gserv/error', err)
      sys.exit(2)

    self.pattern_classes = {
      "BLANK": SolidPattern,
      "GREEN_CLOCKWISE": SpinPattern,
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
    wiringpi.wiringPiSPISetup(self.spi_port, 2500000)
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
    # 8 Leds each take 9 SPI byes and 1 extra to supress the long initial SPI bit with the OPi
    outbytes = [0] * (1 + 8 * 9)
    byte_idx = 1

    for l in ledList:
      outbytes[byte_idx:byte_idx + 8] = self._grbToSpiData(l)
      byte_idx += 9

    wiringpi.wiringPiSPIDataRW(self.spi_port, bytes(outbytes))

  '''
  Convert the grb ws2812b data to a string of spi data.  Each bit is 0.4 uS (1/2,500,000 Hz) to get each bit of the
  ws2812b data to be 1.20uS long (3 bits).  1's are encoded as 110, .80uS high, .4 uS low. 0's are encoded as 100,
  .40uS high, .80uS low.  The orange Pi has a weird long starting bit (10uS longer than it is supposed to), which throws off the timing,
  so a 0 byte is sent out the SPI pin first, before the actual bit stream is sent
  '''
  def _grbToSpiData(self, grb):
    retbytes = [0] * 9
    shift_bit = 5
    idx = 0
    for x in grb:
      for b in range(7, -1, -1):
        if x & 1 << b:
          bit_pat = 6
        else:
          bit_pat = 4

        if shift_bit > -1:
          retbytes[idx] |= bit_pat << shift_bit
          shift_bit -= 3
        else:
          '''
          shift bits right to fill out the last of the byte (shift_byte is negitive here)
          '''
          retbytes[idx] |= bit_pat >> -shift_bit

          '''
          get the remainder by masking out the bits from the last byte (2 ^ bits) -1, and shift
          the remainder to the front of the next byte
          '''
          idx += 1
          retbytes[idx] |= ((pow(2, -shift_bit) - 1) & bit_pat) << 8 + shift_bit
          shift_bit = 8 + shift_bit - 3

    return retbytes


def main():
  ledsMod = LedsModule('config/leds.yaml', 'config/secure.yaml')
  logger = logging.getLogger(__name__)
  logger.info("LedsModule starting")
  ledsMod.run()


if __name__ == "__main__":
  main()
