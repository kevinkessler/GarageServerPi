'''
Thingspeak Publishing Module for Garage Server
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
import requests
import logging
import time
import sys


class ThingspeakModule(BaseModule):
  def __init__(self, config_file, secure_file):
    BaseModule.__init__(self, config_file, secure_file)

    try:
      self.lux_topic = self.config['lux_topic']
      self.temp_topic = self.config['temp_topic']
      self.hum_topic = self.config['hum_topic']
      self.api_key = self.config['thingspeak_api_key']
    except KeyError as e:
      logger = logging.getLogger(__name__)
      err = "Key error in Thingspeak Init: {}".format(e)
      logger.error(err)
      self.mqtt_client.publish('gserv/error', err)
      sys.exit(2)

    self.lux = -1
    self.temp = -1
    self.hum = -1

  def run(self):
    self.mqtt_client.loop_start()

    while True:
      time.sleep(60)
      with open('/etc/armbianmonitor/datasources/soctemp', 'r') as f:
        t = f.read()
      cpu_temp = int(t)

      payload = ('api_key=' + self.api_key + '&field1=' + self.lux +
        '&field2=' + self.temp + '&field3=' + self.hum + '&field4=' + str(cpu_temp))
      r = requests.post('https://api.thingspeak.com/update', data=payload)
      if r.status_code != 200:
        logger = logging.getLogger(__name__)
        logger.warn("Error calling ThingSpeak {}, {}".format(r.status_code, r.text))

  def on_message(self, client, userdata, message):
    msg = message.payload.decode('utf-8')
    if message.topic == self.lux_topic:
      self.lux = msg
    elif message.topic == self.temp_topic:
      self.temp = msg
    elif message.topic == self.hum_topic:
      self.hum = msg

    else:
      logger = logging.getLogger(__name__)
      logger.warn("Unknown Sensor Reading on {}, {}".format(message.topic, msg))


def main():
  thingMod = ThingspeakModule('config/thingspeak.yaml', 'config/secure.yaml')
  logger = logging.getLogger(__name__)
  logger.info("ThingspeakModule starting")
  thingMod.run()


if __name__ == "__main__":
  main()

