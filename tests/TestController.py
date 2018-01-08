import pytest
import multiprocessing
from gserv.ControllerModule import ControllerModule
import paho.mqtt.client as mqtt
import threading
import time
import sys


class ControllerAdapter(multiprocessing.Process):
  def __init__(self):
    multiprocessing.Process.__init__(self)
    self.controller = None
    self.daemon = True

  def run(self):
    self.controller = ControllerModule('./config/controller.yaml', './config/secure.yaml')
    self.controller.set_alarm_times(2, 2, 2, 1)
    self.controller.run()


class MQTTAdapter:
  def __init__(self):
    self.controller = ControllerAdapter()
    self.controller.start()
    self.messages = []
    self.mqtt_client = mqtt.Client('TestController')
    self.mqtt_client.on_connect = self.__on_connect
    self.mqtt_client.on_message = self._on_message
    self.mqtt_client.on_subscribe = self.__on_subscribe
    self.event = threading.Event()
    self.mqtt_client.connect('127.0.0.1')
    self.mqtt_client.loop_start()
    self.event.wait()

  def __on_connect(self, client, userdata, flags, rc):
    if rc != 0:
      print("Cannot connect to MQTT Broker {}".format(rc))
      sys.exit(-1)
    self.mqtt_client.subscribe('#', qos=1)

  def __on_subscribe(self, client, userdata, mid, granted_qos):
    #self.event.set()
    pass

  def _on_message(self, client, userdata, message):
    msg = message.payload.decode('utf-8')
    # Indicates Controller Module is up and running
    if message.topic == 'gserv/gpioinput/open_hall' and msg == '?':
      self.event.set()
    self.messages.append((message.topic, msg))

  def validate_messages(self, expected_messages, actual_messages):
    for x in expected_messages:
      if x not in actual_messages:
        print("{} is not in {}".format(x, actual_messages))
        return False

    return True

  def publish(self, topic, message):
    self.mqtt_client.publish(topic, message)

  '''
  Close the door and clear error state by toggling Hold
  '''
  def close_door(self):
    self.publish('gserv/gpioinput/close_hall', 'LOW')
    self.publish('gserv/gpioinput/open_hall', 'HIGH')
    self.publish('gserv/gpioinput/hold', 'HIGH')
    self.publish('gserv/gpioinput/hold', 'HIGH')
    time.sleep(1)
    self.messages = []


@pytest.fixture(scope='session')
def mqtt_con():
  m = MQTTAdapter()
  return m


@pytest.mark.usefixtures('mqtt_con')
@pytest.mark.dependency()
def test_init(mqtt_con):
  time.sleep(3)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/gpioinput/close_hall', '?'), ('gserv/gpioinput/open_hall', '?')], actual_messages)


@pytest.mark.usefixtures('mqtt_con')
@pytest.mark.dependency(depends=['test_init'])
def test_initial_close(mqtt_con):
  mqtt_con.messages = []
  mqtt_con.publish('gserv/gpioinput/close_hall', 'LOW')
  time.sleep(1)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/leds', 'RED_COUNTERCLOCKWISE')], actual_messages)
  mqtt_con.messages = []
  mqtt_con.publish('gserv/gpioinput/open_hall', 'HIGH')
  time.sleep(1)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/leds', 'GREENCLOCKWISE')], actual_messages)


'''
This test starts with the door closed, opens it, and verifies the auto close
sequence
'''
@pytest.mark.usefixtures('mqtt_con')
@pytest.mark.dependency(depends=['test_initial_close'])
def test_open(mqtt_con):
  mqtt_con.close_door()
  mqtt_con.messages = []
  mqtt_con.publish('gserv/gpioinput/close_hall', 'HIGH')
  time.sleep(1)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/leds', 'CYAN_CLOCKWISE')], actual_messages)
  mqtt_con.messages = []
  mqtt_con.publish('gserv/gpioinput/open_hall', 'LOW')
  time.sleep(1)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/leds', 'COUNTDOWN')], actual_messages)
  mqtt_con.messages = []
  time.sleep(2.5)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/gpiooutput/piezo', 'HIGH')], actual_messages)
  mqtt_con.messages = []
  time.sleep(2.5)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/gpiooutput/door', 'HIGH'),
    ('gserv/gpiooutput/piezo', 'LOW')], actual_messages)
  mqtt_con.messages = []
  mqtt_con.publish('gserv/gpioinput/open_hall', 'HIGH')
  time.sleep(1)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/gpiooutput/piezo', 'LOW'),
    ('gserv/leds', 'CYAN_COUNTERCLOCKWISE')], actual_messages)
  mqtt_con.publish('gserv/gpioinput/close_hall', 'LOW')
  mqtt_con.messages = []
  time.sleep(1)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/camera', '?'),
    ('gserv/leds', 'GREENCLOCKWISE')], actual_messages)


'''
This test starts with the door closed, opens it, and models the garage door not
responding to the close command
'''
@pytest.mark.usefixtures('mqtt_con')
@pytest.mark.dependency(depends=['test_initial_close'])
def test_open_no_response(mqtt_con):
  mqtt_con.close_door()
  mqtt_con.messages = []
  mqtt_con.publish('gserv/gpioinput/close_hall', 'HIGH')
  time.sleep(1)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/leds', 'CYAN_CLOCKWISE')], actual_messages)
  mqtt_con.messages = []
  mqtt_con.publish('gserv/gpioinput/open_hall', 'LOW')
  time.sleep(1)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/leds', 'COUNTDOWN')], actual_messages)
  mqtt_con.messages = []
  time.sleep(2.5)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/gpiooutput/piezo', 'HIGH')], actual_messages)
  mqtt_con.messages = []
  time.sleep(2.5)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/gpiooutput/door', 'HIGH'),
    ('gserv/gpiooutput/piezo', 'LOW')], actual_messages)
  mqtt_con.messages = []
  time.sleep(3)
  actual_messages = mqtt_con.messages
  assert mqtt_con.validate_messages([('gserv/camera', '?'),
    ('gserv/leds', 'RED_CLOCKWISE')], actual_messages)


if __name__ == "__main__":
  m = MQTTAdapter()

