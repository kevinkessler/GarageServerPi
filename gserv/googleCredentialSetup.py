'''
Setup as https://developers.google.com/drive/v3/web/quickstart/python directs
'''
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
import argparse

flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()

SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly', 'https://www.googleapis.com/auth/drive.file']
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Garage Picture Storage'


def get_google_credentials():
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
    This needs to be handled in a user interactive context
    '''
    if not credentials or credentials.invalid:
        client_secret = os.path.join(home_dir, CLIENT_SECRET_FILE)
        flow = client.flow_from_clientsecrets(client_secret, SCOPES)
        flow.user_agent = APPLICATION_NAME
        credentials = tools.run_flow(flow, store, flags)

        print('Storing credentials to ' + credential_path)
    return credentials


def main():
  credentials = get_google_credentials()
  http = credentials.authorize(httplib2.Http())
  service = discovery.build('drive', 'v3', http=http)

  try:
    results = service.files().list(
      pageSize=10, fields="nextPageToken, files(id, name)").execute()
  except Exception as err:
    print("Error: {}".format(err))
  items = results.get('files', [])
  if items:
    print('Files:')
    for item in items:
        print('{0} ({1})'.format(item['name'], item['id']))

  else:
    print("No Files")


if __name__ == '__main__':
  main()
