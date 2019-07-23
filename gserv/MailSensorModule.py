'''
MailSensor Module for Garage Server
Copyright (C) 2019 Kevin Kessler

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
import logging

class MailSensorModule(BaseModule):

  def __init__(self, config_file, secure_file):
    BaseModule.__init__(self, config_file, secure_file)

  def on_message(self, client, userdata, message):
    msg = message.payload.decode('utf-8')
    logger = logging.getLogger(__name__)
    logger.info(msg)


def main():
  mail = MailSensorModule('./mailsensor.yaml', './secure.yaml')
  logger = logging.getLogger(__name__)
  logger.info("MailSensorModule starting")
  mail.run()

if __name__ == "__main__":
  main()