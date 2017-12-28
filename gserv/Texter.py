'''
Texter Class for Garage Server
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
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import threading
import os
import logging


class Texter():
  def __init__(self, config, mqtt_client):
    self.smtp_user = config['smtp_user']
    self.smtp_password = config['smtp_password']
    self.to_addrs = config['to_addrs']
    self.smtp_server = config['smtp_server']
    self.smtp_port = config['smtp_port']
    self.camera_topic = config['camera_topic']
    self.camera_delay = config['picture_delay']
    self.mqtt_client = mqtt_client
    self.pic_timer = None

  '''
  send_text accepts a message and a boolean to take a picture and include it in the text.
  If send_pic is False, just send the text, otherwise, send a message to the camera module
  and wait for a response before sending the text. If aleady waiting on a picture, just send
  the text
  '''
  def send_text(self, message_text, send_pic):
    if send_pic:
      if self.pic_timer is not None:
        self._mail_text(message_text, None)
      else:
        self.mqtt_client.publish(self.camera_topic, '?')
        self.pic_timer = threading.Timer(self.camera_delay, self._failed_pic,
          args=[message_text])
        self.pic_timer.start()
    else:
      self._mail_text(message_text, None)

  '''
  process_message accepts a filename and, if waiting to send a text message,
  calls the text sending funtion. This function may be fed from another class
  listening to the mqtt camera topic
  '''
  def receive_picture(self, picture_path):
    if self.pic_timer is not None:
      self.pic_timer.cancel()
      message_text = self.pic_timer.args[0]
      self.pic_timer = None
      self._mail_text(message_text, picture_path)

  '''
  _mail_text connects to the smtp server and sends the mms email
  '''
  def _mail_text(self, message_text, picture_path):
    logger = logging.getLogger(__name__)
    try:
      s = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20)
    except Exception as err:
      logger.error("Texter SMTP Connect error: {}".format(err))
      return

    try:
      s.starttls()
    except smtplib.SMTPNotSupportedError as err:
      logger.error("Texter TLS Error: {}".format(err))
      return

    try:
      s.login(self.smtp_user, self.smtp_password)
    except smtplib.SMTPAuthenticationError as err:
      logger.error("Texter authentication error: {}".format(err))

    msg = MIMEMultipart()
    msg.attach(MIMEText(message_text, 'plain'))
    if picture_path is not None:
      if os.path.isfile(picture_path):
        with open(picture_path, 'rb') as fp:
          img = MIMEImage(fp.read(), _subtype='jpg')
          msg.attach(img)
      else:
        logger.error("Texter Picture Path {} is not a file".format(picture_path))

    try:
      s.sendmail(self.smtp_user, self.to_addrs, msg.as_string())
    except Exception as err:
      logger.error("Texter Send Mail error: {}".format(err))

    s.quit()

  '''
  _failed_pic is called after the timeout waiting for a picture response. The message text
  without the picture is sent
  '''
  def _failed_pic(self, message_text):
    logger = logging.getLogger(__name__)
    logger.error("Texter timed out waiting for picture")

    self._mail_text(message_text, None)
