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
from gserv.Button import Button
from multiprocessing import Pipe
import wiringpi
import threading
import logging


class GPIOInputModule(BaseModule):

  def __init__(self, config_file, secure_file):
    BaseModule.__init__(self, config_file, secure_file)

    logger = logging.getLogger(__name__)
    if "buttons" not in self.config:
      logger.error("No buttons Configuration in {}".config_file)
      self.config['buttons'] = []

    self.button_pipes = {}
    (self.recvQueue, q) = Pipe()

    for b in self.config["buttons"]:
      try:
        getattr(wiringpi.GPIO, b["pupdown"])
      except AttributeError:
        logger.error("Button On topic {}, pupdown value {} is invalid".format(b["topic"], b["pupdown"]))
        continue

      try:
        getattr(wiringpi.GPIO, b["edge_type"])
      except AttributeError:
        logger.error("Button On topic {}, pupdown value {} is invalid".format(b["topic"], b["edge_type"]))
        continue

      (parent_pipe, child_pipe) = Pipe()
      self.button_pipes[b['topic']] = parent_pipe
      bobj = Button(b["pin"], b["edge_type"], b["debounce"] / 1000.0, b["pupdown"], b["topic"], child_pipe)
      bobj.start()

      t = threading.Thread(name="queueReader" + b["topic"], target=self._pipeThread, args=(b["topic"],))
      t.setDaemon(True)
      t.start()

  def on_message(self, client, userdata, message):
    msg = message.payload.decode('utf-8')
    if msg == '?':
      if message.topic in self.button_pipes:
        self.button_pipes[message.topic].send('?')

  def _pipeThread(self, topic):
    while True:
      msg = self.button_pipes[topic].recv()
      if isinstance(msg, list) and len(msg) == 2:
        self.mqtt_client.publish(msg[0], msg[1], qos=1)


def main():
  giMod = GPIOInputModule('config/gpioinput.yaml', 'config/secure.yaml')
  logger = logging.getLogger(__name__)
  logger.info("GPIOInputModule starting")
  giMod.run()


if __name__ == "__main__":
  main()
