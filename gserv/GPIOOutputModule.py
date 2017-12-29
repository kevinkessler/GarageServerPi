'''
GPIO Input Control Module for Garage Server
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
import logging
import wiringpi
import threading
import sys


class GPIOOutputModule(BaseModule):

  def __init__(self, config_file, secure_file):
    BaseModule.__init__(self, config_file, secure_file)

    wiringpi.wiringPiSetup()

    logger = logging.getLogger(__name__)
    if "outputs" not in self.config:
      logger.error("No outputs Configuration in {}".config_file)
      self.config['outputs'] = []

    self.outputs = {}
    for o in self.config['outputs']:
      try:
        topic = o['topic']
        logger.debug("Setting up output on {}".format(topic))
        self.outputs[topic] = {}
        self.outputs[topic]['type'] = o['type']
        self.outputs[topic]['initial_state'] = o['initial_state']
        self.outputs[topic]['pin'] = o['pin']
        if o['type'] == 'momentary':
          self.outputs[topic]['active_time'] = o['active_time']
      except KeyError as e:
        err = "Key error in GPIOOutputModule Init: {}".format(e)
        logger.error(err)
        self.mqtt_client.publish('gserv/error', err)
        sys.exit(2)

      wiringpi.pinMode(o['pin'], wiringpi.GPIO.OUTPUT)
      wiringpi.digitalWrite(o['pin'], self._gpio_value(o['initial_state']))

  def on_message(self, client, userdata, message):
    logger = logging.getLogger(__name__)
    msg = message.payload.decode('utf-8')
    if msg != 'HIGH' and msg != 'LOW':
      return
    if message.topic in self.outputs:
      output = self.outputs[message.topic]
      logger.debug("Message {} received on {}".format(msg, message.topic))
      if output['type'] == 'toggle':
        wiringpi.digitalWrite(output['pin'], self._gpio_value(msg))
      else:
        if msg != output['initial_state']:
          wiringpi.digitalWrite(output['pin'], self._gpio_value(msg))
          threading.Timer(output['active_time'], self._reset_output, args=[output]).start()

  def _reset_output(self, output):
    wiringpi.digitalWrite(output['pin'], self._gpio_value(output['initial_state']))

  def _gpio_value(self, string):
    if string == "HIGH":
      return wiringpi.HIGH
    else:
      return wiringpi.LOW


def main():
  goMod = GPIOOutputModule('config/gpiooutput.yaml', 'config/secure.yaml')
  logger = logging.getLogger(__name__)
  logger.info("GPIOOutputModule starting")
  goMod.run()


if __name__ == "__main__":
  main()
