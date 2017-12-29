import pytest
from gserv.ControllerModule import ControllerModule
import paho.mqtt.client as mqtt
import threading
import time

class TestController:
  @pytest.fixture(scope='session')
  def mqtt(self):
    print ('Connecting to MQTT')
    self.messages = []
    self.mqtt_client = mqtt.Client('TestController')
    self.mqtt_client.on_connect = self.__on_connect
    self.mqtt_client.on_message = self.on_message
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
    self.event.set()

  def on_message(self, client, userdata, message):
    msg = message.payload.decode('utf-8')
    print('Recevied {} on {}'.format(msg, message.topic))
    self.messages.append((message.topic, msg))

  def _validate_messages(self, expected_messages, actual_messages):
    for x in expected_messages:
      if not x in actual_messages:
        print("{} is not in {}".format(x, actual_messages))
        return False

    return True

  @pytest.mark.usefixtures('mqtt')
  @pytest.mark.dependency()
  def test_init(self):
    self.messages = []
    self.controller = ControllerModule('./config/controller.yaml', './config/secure.yaml')
    time.sleep(3)
    actual_messages = self.messages
    assert self._validate_messages([('gserv/gpioinput/close_hall', '?'), ('gserv/gpioinput/open_hall', '?')], actual_messages)

  @pytest.mark.usefixtures('mqtt')
  @pytest.mark.dependency(depends=['test_init'])
  def test_initial_close(self):
    self.messages = []
    self.mqtt_client.publish('gserv/gpioinput/close_hall', 'LOW')
    time.sleep(1)
    actual_messages = self.messages
    print(self.controller)
    print(actual_messages)
    assert self._validate_messages([], actual_messages)


if __name__ == '__main__':
  t = TestController()
  t.test_init()
