'''
Controller Module for Garage Server
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
from gserv.Texter import Texter
from gserv.PIR import PIR
import sys
import logging
import enum
import threading


class ControllerModule(BaseModule):

  def __init__(self, config_file, secure_file):
    BaseModule.__init__(self, config_file, secure_file)

    try:
      self.input_topic = self.config['input_topic']
      self.piezo_topic = self.config['piezo_topic']
      self.camera_topic = self.config['camera_topic']
      self.close_input = self.config['close_input']
      self.open_input = self.config['open_input']
      self.hold_input = self.config['hold_input']
      self.pir_input = self.config['pir_input']
      self.light_level_topic = self.config['light_level_topic']
      self.hold_led = self.config['hold_led']
      self.led_topic = self.config['led_topic']
      self.piezo_topic = self.config['piezo_topic']
      self.door_control_topic = self.config['door_control_topic']
    except KeyError as e:
      logger = logging.getLogger(__name__)
      err = "Key error in Controller Init: {}".format(e)
      logger.error(err)
      self.mqtt_client.publish('gserv/error', err)
      sys.exit(2)

    self.open_state = "XX"
    self.close_state = "XX"

    self.door_close_timer = None
    self.command_response_timer = None
    self.on_hold = False
    self.error_state = False

    self.states = enum.Enum('DoorStates', 'CLOSED OPENED CLOSING OPENING UNKNOWN')
    self.current_state = self.states.UNKNOWN

    self.force_close = False

    self.led_mapping = {
      "CLOSED": "GREENCLOCKWISE",
      "OPENED": "COUNTDOWN",
      "CLOSING": "CYAN_COUNTERCLOCKWISE",
      "OPENING": "CYAN_CLOCKWISE",
      "UNKNOWN": "RED_COUNTERCLOCKWISE",
      "HOLD": "BLUE_CLOCKWISE",
      "ERROR": "RED_CLOCKWISE"
    }

    self.texter = Texter(self.mqtt_client)
    self.PIR = PIR(self.config, self.mqtt_client)

    self._get_door_state()

  '''
  MQTT Message Handler
  '''
  def on_message(self, client, userdata, message):
    msg = message.payload.decode('utf-8')
    if message.topic == self.camera_topic:
      if msg != '?':
        self.texter.receive_picture(msg)
    elif message.topic == self.light_level_topic:
      self.PIR.light_level(msg)
    elif message.topic.startswith(self.input_topic):
      input_list = message.topic.split('/')
      input = input_list[len(input_list) - 1]
      self._process_inputs(input, msg)

  '''
  _get_door_state sends MQTT Messages to the input module requesting
  the module to send the current state of the hall switches indicating
  the door position
  '''
  def _get_door_state(self):
    self.mqtt_client.publish(self.input_topic + '/' + self.close_input, '?')
    self.mqtt_client.publish(self.input_topic + '/' + self.open_input, '?')

  '''
  _process_inputs handles the input messages from the MQTT handler.
  '''
  def _process_inputs(self, input, state):
    if input == self.hold_input:
      if state == "HIGH":
        self._process_hold()
    elif input == self.pir_input:
      self.PIR.motion_detected(state)
    elif input == self.close_input or input == self.open_input:
      self._process_hall_sensors(input, state)

  '''
  _process_hall_sensors evaluates state changes to the door sensors and set the led
  ring display to the appropriate pattern. If the door is opened, the auto close timer is
  started. If closed, the timer is canceled. If the state change is was the result of a
  auto close timer, the appropriate text message is sent: OPENED after a force close means
  a problem occurred.
  '''
  def _process_hall_sensors(self, input, state):
    if self.command_response_timer is not None:
      logger = logging.getLogger(__name__)
      logger.debug("Command Delay Timer canceled")
      self.command_response_timer.cancel()
      self.command_response_timer = None

    if input == self.close_input:
      self.close_state = state
    elif input == self.open_input:
      self.open_state = state

    if self.close_state == "LOW" and self.open_state == "HIGH":
      self.current_state = self.states.CLOSED
      self._stop_timer()
      if self.force_close:
        self.texter.send_text("Garage Door Closed Successfully", True)
        self.force_close = False
    elif self.close_state == "HIGH" and self.open_state == "LOW":
      self.current_state = self.states.OPENED
      if self.force_close:
        self.error_state = True
        self.force_close = False
        logger = logging.getLogger(__name__)
        logger.error("Force Close Failed")
        self.texter.send_text("Garage Door Closing FAILED", True)
      else:
        self._start_timer()
    elif self.close_state == "HIGH" and self.open_state == "HIGH":
      self._stop_timer()
      if input == self.close_input:
        self.current_state = self.states.OPENING
      else:
        self.current_state = self.states.CLOSING
    else:
      self._stop_timer()
      self.current_state = self.states.UNKNOWN

    logger = logging.getLogger('door_state')
    logger.info(self.current_state.name)

    self._set_ring_leds(self.current_state.name)

  '''
  _stop_timer cancels the timer thread, if it exists
  '''
  def _stop_timer(self):
    logger = logging.getLogger(__name__)
    logger.debug("Stopping Door Timer")
    self._piezo("OFF")
    self.on_hold = False
    if self.door_close_timer is not None:
      logger.debug("Stopping timer {}".format(self.door_close_timer.getName()))
      self.door_close_timer.cancel()
    self.door_close_timer = None

  '''
  _start_timer starts the 9 minute 30 second timer, during which the auto close waits
  in silence. The final 30 second wait has the piezo alarm sounding
  '''
  def _start_timer(self):
    if not self.on_hold and self.door_close_timer is None:
      self.door_close_timer = threading.Timer(570.0, self._nine_thirty_timer)
      self.door_close_timer.start()
      logger = logging.getLogger(__name__)
      logger.debug("Starting Door Timer {}".format(self.door_close_timer.getName()))

  '''
  _process_hold toggle the state of the hold input. If turned ON, the auto close timer
  is canceled, if running, the led ring display shows the HOLD pattern, and the HOLD Led
  is turned on. If turned OFF, the timer is started is the door is opened, the ring LED
  display is set to the display pattern appropriate for the current door state, and the
  hold led is turned off. Toggling Hold also clears the error state
  '''
  def _process_hold(self):
    self.error_state = False
    logger = logging.getLogger('door_state')
    if self.on_hold is False:
      self._stop_timer()
      self.on_hold = True
      self._set_ring_leds("HOLD")
      self.mqtt_client.publish(self.hold_led, "HIGH")
      logger.info("HOLD ON")
    else:
      self.on_hold = False
      if self.current_state == self.states.OPENED:
        self._start_timer()
      self._set_ring_leds(self.current_state.name)
      self.mqtt_client.publish(self.hold_led, "LOW")
      logger.info("HOLD OFF")

  '''
  _nine_thirty_timer is executed after 9 minutes 30 seconds of waiting for the auto close
  timer. The piezo alarm is sounded for the last 30 seconds.
  '''
  def _nine_thirty_timer(self):
    logger = logging.getLogger(__name__)
    logger.debug("9:30 Timer Expired")
    self._piezo("ON")
    self.door_close_timer = threading.Timer(30.0, self._final_close_timer)
    self.door_close_timer.start()

  '''
  _final_close_timer is run at the expiration of the auto close timer. It sends the command
  to close the door, turns off the piezo alarm and sets the force_close flag. Launches
  a timer which generates an error state if the door doesn't start moving within 10 seconds
  of the command to close the door
  '''
  def _final_close_timer(self):
    logger = logging.getLogger(__name__)
    logger.debug("Final Timer expired")
    self.countdown_timer = None
    self.mqtt_client.publish(self.door_control_topic, "HIGH")
    self._piezo("OFF")
    self.force_close = True
    self.command_response_timer = threading.Timer(10.0, self._door_move_failed)
    self.command_response_timer.start()

  '''
  _door_move_failed is called if the door was told to close, but did not
  respond within 10 seconds
  '''
  def _door_move_failed(self):
    logger = logging.getLogger(__name__)
    logger.error("Garage Door did not respond to close")
    self.texter.send_text("Garage Door did not respond to close command", True)
    self.force_close = False
    self.error_state = True
    self._set_ring_leds("ERROR")
  '''
  _set_ring_leds sets the ring leds to the appropriate pattern
  '''
  def _set_ring_leds(self, state):
    if self.error_state is True:
      self.mqtt_client.publish(self.led_topic, self.led_mapping["ERROR"])
    else:
      self.mqtt_client.publish(self.led_topic, self.led_mapping[state])

  def _piezo(self, state):
    if state == "OFF":
      self.mqtt_client.publish(self.piezo_topic, "LOW")
    else:
      self.mqtt_client.publish(self.piezo_topic, "HIGH")


def main():
  controlMod = ControllerModule('config/controller.yaml', 'config/secure.yaml')
  logger = logging.getLogger(__name__)
  logger.info("ControllerModule starting")
  controlMod.run()


if __name__ == "__main__":
  main()