#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import json
import sys
import requests

freebox_config_file = os.path.join(os.path.dirname(__file__), 'freebox.json')


class Freebox:
    uid = None
    api_base_url = None
    device_type = None
    app_token = None
    ip = None

    session_challenge = None
    session_token = None

    def __init(self, uid, api_base_url, device_type):
        self.uid = uid
        self.api_base_url = api_base_url
        self.device_type = device_type

    @staticmethod
    def get_api_call_uri(endpoint):
        return 'http://mafreebox.freebox.fr/api/v3/' + endpoint

    def save(self):
        with open(freebox_config_file, 'w') as output:
            json.dump(self.__dict__, output)

    @staticmethod
    def retrieve():
        freebox = Freebox()
        with open(freebox_config_file, 'r') as input:
            freebox.__dict__ = json.load(input)

        return freebox


def api_authorize(app_id, app_name, app_version, device_name):
    print('Authorizing...')
    uri = Freebox.get_api_call_uri('login/authorize/')
    r = requests.post(uri, json={
        'app_id': app_id,
        'app_name': app_name,
        'app_version': app_version,
        'device_name': device_name
    })

    r_json = r.json()

    if not r_json['success']:
        print('Error while authenticating: {}'.format(r_json))
        sys.exit(1)

    app_token = r_json['result']['app_token']
    track_id = r_json['result']['track_id']

    # Watch for token status
    print('Waiting for you to push the "Yes" button on your Freebox')

    challenge = None
    while True:
        r2 = requests.get(uri + str(track_id))
        r2_json = r2.json()
        status = r2_json['result']['status']

        if status == 'pending':
            sys.stdout.write('.')
            sys.stdout.flush()
        elif status == 'timeout':
            print('\nAuthorization request timeouted. Re-run this script, but please go faster next time')
            sys.exit(1)
        elif status == 'denied':
            print('\nYou denied authorization request.')
            sys.exit(1)
        elif status == 'granted':
            challenge = r2_json['result']['challenge']
            break

    freebox = Freebox()
    freebox.app_token = app_token
    freebox.session_challenge = challenge
    freebox.save()

    # That's a success
    print('\nSuccessfully authenticated script. Exiting.')

    sys.exit(0)


def encode_app_token(app_token, challenge):
    import hashlib
    import hmac

    return hmac.new(str.encode(app_token), str.encode(challenge), hashlib.sha1).hexdigest()


def api_open_session(freebox, app_id):
    # Retrieve challenge
    uri = Freebox.get_api_call_uri('login/')
    r = requests.get(uri)
    r_json = r.json()

    if not r_json['success']:
        print('Could not retrieve challenge when opening session: {}'.format(r_json['msg']))
        sys.exit(1)

    challenge = r_json['result']['challenge']
    freebox.session_challenge = challenge

    # Open session
    uri += 'session/'
    password = encode_app_token(freebox.app_token, challenge)
    r = requests.post(uri, json={
        'app_id': app_id,
        'password': password
    })
    r_json = r.json()

    if not r_json['success']:
        print('Could not open session: {}'.format(r_json['msg']))
        sys.exit(1)

    session_token = r_json['result']['session_token']
    freebox.session_token = session_token
    freebox.save()


def get_freebox():
    return Freebox.retrieve()
