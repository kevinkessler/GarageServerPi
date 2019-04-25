'''
Light Module for Garage Server
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
import time
import logging
import threading
import sys


class LightModule(BaseModule):

  def __init__(self, config_file, secure_file):
    BaseModule.__init__(self, config_file, secure_file)
    try:
      self.on_time = self.config['on_time']
      self.light_switch = self.config['light_switch']
      self.light_level_topic = self.config['light_level_topic']
      self.light_control_topic = self.config['light_control_topic']
    except KeyError as e:
      logger = logging.getLogger(__name__)
      err = "Key error in Camera Init: {}".format(e)
      logger.error(err)
      self.mqtt_client.publish('gserv/error', err)
      sys.exit(2)

    self.cur_lux = -1
    self.lighting_timer = None

  def on_message(self, client, userdata, message):
    msg = message.payload.decode('utf-8')
    if message.topic == self.light_control_topic:
      if msg == 'ON':
        self._turn_on()
      elif msg == 'OFF':
        self._turn_off()
    elif message.topic == self.light_level_topic:
      self.cur_lux = msg

  def _turn_on(self):
    before_lux = self.cur_lux
    self.mqtt_client.publish(self.light_level_topic, "HIGH")
    time.sleep(5)
    if self.cur_lux < before_lux + 1:
      self.mqtt_client.publish(self.light_level_topic, "HIGH")
    self.lighting_timer = threading.Timer(self.on_time, self._turn_off())

  def _turn_off(self):
    if self.lighting_timer is not None:
      self.lighting_timer.stop()
      self.lighting_timer = None

    before_lux = self.cur_lux
    self.mqtt_client.publish(self.light_level_topic, "HIGH")
    time.sleep(5)
    if self.cur_lux > before_lux + 1:
      self.mqtt_client.publish(self.light_level_topic, "HIGH")


def main():
  lightMod = LightModule('config/light.yaml', 'config/secure.yaml')
  logger = logging.getLogger(__name__)
  logger.info("LightModule starting")
  lightMod.run()


if __name__ == "__main__":
  main()
