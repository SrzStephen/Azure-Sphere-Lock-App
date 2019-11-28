import json
from knobs import Knob
from flask import Flask, flash, render_template, request
from requests import post, get
from wtforms import (Form, StringField, SelectField)
import os
import logging
from src.sql import UserClass
import time
from threading import Thread

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
DEBUG = False
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
UserClass = UserClass()


class EndpointClass:

    def __init__(self):
        self.api_endpoint_base = Knob(env_name="AZURE_API_ENDPOINT", default="www.google.com",
                                      description="C# API endpoint")
        self.api_access_key = Knob(env_name="AZURE_API_HOST_KEY", default="12345678", description="C# API host key")

    def direct_call(self, method, payload, device):
        url = f"{self.api_endpoint_base.get()}/api/DirectCall/?code={self.api_access_key.get()}"
        logger.debug("Making request with url {url}")
        headers = {"method_name": method, "target_device": device}
        response = post(url, headers=headers, data=payload)
        try:
            return True, response.json()
        except json.JSONDecodeError:
            return False, f"Error: {response.content}"

    def get_devices(self):
        url = f"{self.api_endpoint_base.get()}/api/GetDevices/?code={self.api_access_key.get()}"
        response = get(url)
        try:
            if response.status_code == 200:
                device_list = []
                for device in response.json():
                    device_list.append(dict(name=device['device_name'], online=device['device_status']))
                return device_list
            else:
                logger.warning(f"Failed to get device list from url {url}")
                logger.debug(f"{response.status_code}  {response.content}")
            return response
        except json.JSONDecodeError:
            logger.error(f"Non JSON response returned for 200 error code at {url}")


def update_device(device_name):
    logger.debug(f"device_name      {device_name}")
    device_list = UserClass.get_device_entries_as_list(device_name)
    logger.debug(f"{device_list}")
    if len(device_list) is not 0:
        api = EndpointClass()
        # keep running every minute until data gets put in successfully.
        while (True):
            status, result = api.direct_call('put_data', json.dumps(device_list), device_name)
            if bool(status):
                flash("User successfully added")
                return
            time.sleep(60)


def parse_request(message: dict):
    if "Message" in message:
        # looks like a microsoft IOT hub message
        msg = json.loads(message['Message'])
        error_code = msg['errorCode']
        error_message = msg['message']
        return f"Error: IOTHUB error {error_code} \n {error_message}"
    elif "payload" in message:
        success = bool(message['payload']['success'])
        response_message = message['payload']['message']
        if success:
            return f"{response_message}"
        else:
            return f"Error: Message"

class ReusableForm(Form):
    choices = []
    api = EndpointClass()
    device_list = api.get_devices()
    if device_list is None:
        choices = [("No device found", "No device found")]
    else:
        for item in device_list:
            choices.append((item['name'],f"{item['name']} ({'online' if item['online'] == 1 else 'offline'})"))

    device_name = SelectField("device_name", choices=choices)
    username = StringField("username")


@app.route("/", methods=['GET', 'POST'])
def main():
    form = ReusableForm(request.form)
    api = EndpointClass()
    if request.method == 'POST':
        device_name = request.form['device_name']
        username = request.form['username']

        if "add_user" in request.form:
            status, result = api.direct_call("add_user", {}, device_name)
            if status:
                if bool(result.get("success", False)):
                    card_id = result.get("message")
                    # delete old user if they exist
                    if UserClass.user_exists(username, device_name):
                        UserClass.update_user(username, card_id, device_name)
                        flash(f"Found {username} on device {device_name} to have UID {card_id}. Trying to add user")
                        update_device(device_name)
                    else:
                        UserClass.add_user(username, card_id, device_name)
                        flash(f"Added {username} on device {device_name} to have UID {card_id}. Trying to add user")
                        update_device(device_name)
            else:
                flash(result)

        elif "remove_user" in request.form:
            try:
                if UserClass.user_exists(username, device_name):
                    UserClass.remove_user(username, device_name)
                    flash(f"removed {username} from {device_name} database")
                    Thread(target=update_device, args=[device_name]).start()
                else:
                    flash(f"User {username} doesn't exist on {device_name}")

            except Exception as e:
                flash(f"Failed to remove user. Error {e}")

        elif "remote_open" in request.form:
            status, result = api.direct_call("remote_open", payload={}, device=device_name)
            if status:
                if bool(result.get("success", False)):
                    flash(f"Opened door {device_name}")
                else:
                    flash(f"Failed to open door on {device_name}")
        else:
            flash("Unknown command")

    return render_template('index.html', form=form)


if __name__ == "__main__":
    app.run()
