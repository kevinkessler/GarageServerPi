'''
PIR Class for Garage Server
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

import threading
import logging


class PIR():
  def __init__(self, config, mqtt_client):
    self.camera_topic = config['camera_topic']
    self.light_switch = config['light_switch']
    self.min_light_level = config['min_light_level']
    self.retrigger_delay = config['retrigger_delay']
    self.snapshot_delay = config['snapshot_delay']

    self.mqtt_client = mqtt_client

    self.retrigger_timer = None
    self.snapshot_timer = None

    self.light_level = None

  def light_level(self, lux):
    self.light_level = int(lux)

  def motion_detected(self, motion):
    logger = logging.getLogger(__name__)
    if self.retrigger_timer is None and motion == "HIGH":
      logger.debug("PIR Detected Motion, taking snapshot")
      self.retrigger_timer = threading.Timer(self.retrigger_delay, self._retrigger_timer_expire)
      self.retrigger_timer.start()
      self.snapshot_timer = threading.Timer(self.snapshot_delay, self._take_snapshot)
      self.snapshot_timer.start()
      if self.light_level is not None and self.light_level < self.min_light_level:
        self.mqtt_client.publish(self.light_switch, "ON")
    else:
      logger.debug("PIR Motion Detected, still within the retrigger delay")

  def _retrigger_timer_expire(self):
    self.retrigger_timer = None

  def _take_snapshot(self):
    logger = logging.getLogger(__name__)
    logger.debug("Sending Camera MQTT command")
    self.mqtt_client.publish(self.camera_topic, "?")
