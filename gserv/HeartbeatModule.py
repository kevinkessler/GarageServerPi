'''
Heartbeat Module for Garage Server
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

'''
This module generates periodic logging under the tag of heartbeat, which can be monitored
by an Amazon Lambda service to alert if the Orange Pi becomes unresponsive
'''


class HeartbeatModule(BaseModule):

  def __init__(self, config_file, secure_file):
    BaseModule.__init__(self, config_file, secure_file)

  def run(self):
    logger = logging.getLogger(__name__)
    self.mqtt_client.loop_start()
    while True:
      logger.info("Heartbeat")
      time.sleep(300)


def main():
  hbMod = HeartbeatModule('config/heartbeat.yaml', 'config/secure.yaml')
  logger = logging.getLogger(__name__)
  logger.info("HeartbeatModule starting")
  hbMod.run()


if __name__ == "__main__":
  main()
