from flask import Flask, request
import requests
from Crypto.PublicKey import RSA
import os
import json
import jws


app = Flask(__name__)
app.config.from_object(os.environ.get('SETTINGS'))


@app.route("/")
def check_status():
    return "Everything is OK"


@app.route("/sign", methods=["POST"])
def new_title_version():
    title = json.dumps(request.get_json())
    signed_title = return_signed_data(title)
    return str(signed_title)


@app.route("/verify", methods=["POST"])
def verify_title_version():

    signed_title = request.get_json()

    signature = signed_title['sig']

    #signed_data is currently unicode.  Incompatible with JWS.  Convert to ASCII
    signature = signature.encode('ascii', 'ignore')
    title = json.dumps(signed_title['data'])

    # #import keys
    key_data = open('test_keys/test_public.pem').read()
    key = RSA.importKey(key_data)

    header = { 'alg': 'RS256' }
    the_result = jws.verify(header, title, signature, key)

    if the_result:
        return "verified"
    else:
        return "you'll never see this message, jws will show its own."


@app.route("/insert", methods=["POST"])
def insert_new_title_version():
    data_dict = request.get_json()
    data = json.dumps(data_dict)
    signed_data = return_signed_data(data)
    save_this = build_system_of_record_json_string(data_dict, signed_data)

    server = app.config['SYSTEM_OF_RECORD']
    route = '/insert'
    url = server + route

    headers = {'Content-Type': 'application/json'}

    response = requests.post(url, data=json.dumps(save_this), headers=headers)

    return response.text


def return_signed_data(data):

    #import keys
    key_data = open('test_keys/test_private.pem').read()
    key = RSA.importKey(key_data)

    header = { 'alg': 'RS256' }

    sig = jws.sign(header, data, key)

    return str(sig)


def build_system_of_record_json_string(original_data_dict, signed_data_string):

    system_of_record_dict = {"data": original_data_dict, "sig":signed_data_string}
    system_of_record_json = json.dumps(system_of_record_dict)

    return system_of_record_json
