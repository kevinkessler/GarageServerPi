import paho.mqtt.client as mqtt
import sys
import os
import yaml
import logging
import logging.config


class BaseModule(object):
  def __init__(self, config_file, secure_file):
    self.is_connected = False

    self.config = self.__merge_yaml(config_file, secure_file)
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

  """
  Merge the secure yaml entries into the publicly visible config yaml files
  """
  def __merge_yaml(self, config_file, secure_file):
    if os.path.exists(config_file):
      with open(config_file, 'r') as f:
        config_str = f.read()
    else:
      print("Config File Not Found")
      sys.exit(-1)

    if os.path.exists(secure_file):
      with open(secure_file, 'r') as f:
        secure_yaml = yaml.safe_load(f)
    else:
      print("Secure File Not Found")
      sys.exit(-1)

    for replVar in secure_yaml:
      if isinstance(secure_yaml[replVar], str):
          tag = "{{ " + replVar + " }}"
          config_str = config_str.replace(tag, secure_yaml[replVar])

    return yaml.safe_load(config_str)

  def run(self):
    self.mqtt_client.loop_forever()

