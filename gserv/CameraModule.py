'''
Camera Control Module for Garage Server
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
import pygame
import pygame.camera
import httplib2
import sys
import os
from apiclient import discovery
from oauth2client import tools
from oauth2client.file import Storage
from googleapiclient.http import MediaFileUpload
import argparse
import datetime
import logging

'''
Module to take a photo from a USB camera, when a '?' is sent as an MQTT message on the
configured camera topic. Published the file name and local path on the same topic when
complete.
'''


class CameraModule(BaseModule):

  def __init__(self, config_file, secure_file):
    BaseModule.__init__(self, config_file, secure_file)
    try:
      self.camera_device = self.config['camera_device']
      self.image_width = self.config['image_width']
      self.image_height = self.config['image_height']
      self.picture_path = self.config['picture_path']
      self.picture_prefix = self.config['picture_prefix']
      self.camera_topic = self.config['sub_topic']
      self.google_folder = self.config['google_folder']
    except KeyError as e:
      logger = logging.getLogger(__name__)
      err = "Key error in Camera Init: {}".format(e)
      logger.error(err)
      self.mqtt_client.publish('gserv/error', err)
      sys.exit(2)

    self.flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()

    pygame.camera.init()

  def run(self):
    self.mqtt_client.loop_forever()

  def on_message(self, client, userdata, message):
    msg = message.payload.decode('utf-8')
    if msg == '?':
      self._take_picture()

  '''
  _take_picture uses the pygame camera API to take a photo from the USB Camera
  '''
  def _take_picture(self):
    logger = logging.getLogger(__name__)
    logger.debug("Picture Request")

    cam = pygame.camera.Camera(self.camera_device, (self.image_width, self.image_height))

    try:
      cam.start()
    except SystemError as err:
      logger.error("Camera Error: {}".format(err))
      return

    filename = self.picture_prefix + "{:%Y%m%d%H%M%S}.jpg".format(datetime.datetime.now())
    pPath = os.path.join(self.picture_path, filename)
    try:
      image = cam.get_image()
      pygame.image.save(image, pPath)
      cam.stop()
    except Exception as err:
      logger.debug("Camera Error: {}".format(err))
      return

    self.mqtt_client.publish(self.camera_topic, pPath)
    self._google_upload_photo(pPath)

  '''
  _get_google_credentials stolen from Google's example app and slightly modified.
  Gets credential to access Google Drive to store pictures
  '''
  def _get_google_credentials(self):
    """Gets valid user credentials from storage.
    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.
    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
      os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'garage-server.json')

    store = Storage(credential_path)
    credentials = store.get()
    '''
    No interactive context in this module, so just fail
    '''
    if not credentials or credentials.invalid:
      logger = logging.getLogger(__name__)
      logger.error("Invalid Google Credentials")
      credentials = None

    return credentials

  '''
  _google_upload_photo uploads the picture to Google Drive and puts it in the
  configured folder
  '''
  def _google_upload_photo(self, picture_path):
    logger = logging.getLogger(__name__)

    picture_name = os.path.basename(picture_path)
    credentials = self._get_google_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http)

    try:
      results = service.files().list(pageSize=10, fields="nextPageToken, files(id, name)",
        q="mimeType='application/vnd.google-apps.folder' and name='" + self.google_folder +
        "' and trashed=false").execute()
    except Exception as err:
      logger.error("Google Drive Error: {}".format(err))
      return

    items = results.get('files', [])
    if items:
      metadata = {'name': picture_name, 'parents': [items[0]['id']]}
      media = MediaFileUpload(picture_path, mimetype='image/jpeg')
      service.files().create(body=metadata, media_body=media, fields='id').execute()
    else:
      logger.error("Google Drive Error: Couldn't find folder {}".format(self.google_folder))


def main():
  camMod = CameraModule('config/camera.yaml', 'config/secure.yaml')
  logger = logging.getLogger(__name__)
  logger.info("CameraModule starting")
  camMod.run()


if __name__ == "__main__":
  main()
