from common import *
import requests
from trigger import plc_trigger
import threading

def add_image(auth_token):
    part_id = data["data_capture"]["part_id"]
    wids = data["data_capture"]["ws_id"]
    camera_type = list(data["data_capture"]["stream"].keys())[0]
    if camera_type == "Kafka":
        camera_ids = data["data_capture"]["stream"][camera_type].split("_")[1]
    else:
        camera_ids = data["data_capture"]["stream"][camera_type]

    url = "https://dev.livis.ai/api/livis/v1/capture/capture_image/"

    payload = json.dumps({
    "camera_id": str(camera_ids),
    "part_id": str(part_id),
    "workstation_id": str(wids),
    "golden_image": False
    })


    headers = {
    'Authorization': auth_token,
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    return json.loads(response.text)

def trigger_listen():
    print("In data capture")
    # Get auth token from Local Mongo
    t1 = threading.Thread(target=plc_trigger)
    t1.start()
    user_details_col = MongoHelper().getCollection('user_details')
    user_details = user_details_col.find_one()
    auth_token = user_details["token"]

    while True:
        trigger = CacheHelper().get_json("trigger")
        if trigger:
            CacheHelper().set_json({"trigger":False})
            add_image(auth_token)