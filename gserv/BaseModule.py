'''
Base Module for Garage Server
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
import paho.mqtt.client as mqtt
import sys
import os
import yaml
import logging
import logging.config

"""
Merge the secure yaml entries into the publicly visible config yaml files
"""


def merge_yaml(config_file, secure_file):
  if os.path.exists(config_file):
    with open(config_file, 'r') as f:
      config_str = f.read()
  else:
    return {'Error': 'Config File Not Found'}

  if os.path.exists(secure_file):
    with open(secure_file, 'r') as f:
      secure_yaml = yaml.safe_load(f)
  else:
    return {'Error': 'Secure File Not Found'}

  for replVar in secure_yaml:
    if isinstance(secure_yaml[replVar], str):
        tag = "{{ " + replVar + " }}"
        config_str = config_str.replace(tag, secure_yaml[replVar])

  return yaml.safe_load(config_str)


class BaseModule(object):
  def __init__(self, config_file, secure_file):
    self.is_connected = False

    self.config = merge_yaml(config_file, secure_file)
    if 'Error' in self.config:
      print("Error {}".self.config['Error'])
      sys.exit(2)

    if 'logging' in self.config:
      logging.config.dictConfig(self.config['logging'])

    self.mqtt_client = mqtt.Client(self.config['mqtt_client_name'])
    self.mqtt_client.on_connect = self.__on_connect
    self.mqtt_client.on_message = self.on_message
    self.mqtt_client.on_subscribe = self.__on_subscribe
    self.mqtt_client.connect('localhost')

  def __on_connect(self, client, userdata, flags, rc):
    if rc != 0:
      log = logging.getLogger(self.__class__.__name__)
      log.error("Cannot connect to MQTT Broker {}".format(rc))
      print("Cannot connect to MQTT Broker {}".format(rc))
      sys.exit(-1)

    if 'sub_topic' in self.config:
      self.mqtt_client.subscribe(self.config['sub_topic'], qos=1)

    self.is_connected = True

  def on_message(self, client, userdata, message):
    print("Wrong")
    pass

  def __on_subscribe(self, client, userdata, mid, granted_qos):
    log = logging.getLogger(self.__class__.__name__)
    log.debug("Subscribed")
    pass

  def run(self):
    self.mqtt_client.loop_forever()

