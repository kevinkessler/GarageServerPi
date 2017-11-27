'''
Logging Module for Garage Server
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
from multiprocessing.managers import BaseManager
from multiprocessing import Lock
import loggly.handlers
import sys
import os
import yaml
import logging
import logging.config
import json


class LockManager(BaseManager): pass


class UtilityModule(BaseModule):

  def __init__(self, config_file, secure_file):
    BaseModule.__init__(self, config_file, secure_file)

  def on_message(self, client, userdata, message):
    logger = logging.getLogger(__name__)
    logger.info(message.payload.decode('utf-8'))

  def run(self):
    self.lock_i2c = Lock()
    self.lock_spi = Lock()

    LockManager.register('get_i2c_lock', callable=lambda:self.lock_i2c)
    LockManager.register('get_spi_lock', callable=lambda:self.lock_spi)

    server_port = 5000
    if 'lock_port' in self.config:
      server_port = self.config['lock_port']

    m = LockManager(address=('127.0.0.1',server_port), authkey='orangepi'.encode('utf-8'))
    s = m.get_server()

    self.mqtt_client.loop_start()
    s.serve_forever()


def main():
  utility = UtilityModule('./utility.yaml', './secure.yaml')
  utility.run()

if __name__ == "__main__":
  main()