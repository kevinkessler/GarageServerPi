'''
Sensor Module for Garage Server
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
from smbus2 import SMBus
import logging
import sys
import time


class SensorModule(BaseModule):

  def __init__(self, config_file, secure_file):
    BaseModule.__init__(self, config_file, secure_file)

    try:
      self.lux_topic = self.config['lux_topic']
      self.temp_topic = self.config['temp_topic']
      self.hum_topic = self.config['hum_topic']
      self.max_addr = self.config['max_addr']
      self.hih_addr = self.config['hih_addr']
      self.sub_topic = self.config['sub_topic']
    except KeyError as e:
      logger = logging.getLogger(__name__)
      err = "Key error in Sensor Init: {}".format(e)
      logger.error(err)
      self.mqtt_client.publish('gserv/error', err)
      sys.exit(2)

  def run(self):
    self.bus = SMBus(0)

    # Configure MAX44009
    self.bus.write_byte_data(0x4A, 0x02, 0x00)

    self.mqtt_client.loop_start()

    while True:
      self.post_lux()
      self.post_temp()
      time.sleep(1)

  def post_lux(self):
    logger = logging.getLogger(__name__)
    data = self.bus.read_i2c_block_data(self.max_addr, 0x03, 2)
    reading = self.lightReading(data[0], data[1])
    logger.debug("Lux = {}".format(reading))
    self.mqtt_client.publish(self.lux_topic, str(reading), retain=True)

  def post_temp(self):
    logger = logging.getLogger(__name__)
    data = self.bus.read_i2c_block_data(self.hih_addr, 0x00, 4)
    humidity = ((((data[0] & 0x3F) * 256) + data[1]) * 100.0) / 16383.0
    temp = (((data[2] & 0xFF) * 256) + (data[3] & 0xFC)) / 4
    cTemp = (temp / 16384.0) * 165.0 - 40.0
    logger.debug("Hum = {}".format(humidity))
    logger.debug("Temp = {}".format(cTemp))
    self.mqtt_client.publish(self.temp_topic, str(cTemp), retain=True)
    self.mqtt_client.publish(self.hum_topic, str(humidity), retain=True)

  def lightReading(self, data_h, data_l):
    exp = (data_h & 0xF0) >> 4
    mant = ((data_h & 0x0F) << 4) | (data_l & 0x0F)
    return (pow(2, exp) * mant * 0.045)

  def on_message(self, client, userdata, message):
    msg = message.payload.decode('utf-8')
    print(msg)


def main():
  sensorMod = SensorModule('config/sensor.yaml', 'config/secure.yaml')
  logger = logging.getLogger(__name__)
  logger.info("SendorModule starting")
  sensorMod.run()


if __name__ == "__main__":
  main()
