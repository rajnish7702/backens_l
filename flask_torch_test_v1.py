from abc import ABC, abstractmethod
from sys import flags
import cv2
import numpy as np
from datetime import datetime
from flask import Flask, Response
import torch 
import cv2
import redis
import pickle
import threading
from kafka import KafkaConsumer
from Button import Button
from neoapi import neoapi
import json
import wget
import datetime
from flask_cors import CORS
import pymongo
from pymongo import MongoClient
# import tldextract
from os import path

f = open('infer_doc.json')
data = json.load(f)
f.close()

REDIS_HOST = data["server_configs"]["REDIS_HOST"]
REDIS_PORT = data["server_configs"]["REDIS_PORT"]
KAFKA_BROKER_URL=data["server_configs"]["KAFKA_BROKER_URL"]
MONGO_SERVER_HOST = data["server_configs"]["MONGODB_HOST"]
MONGO_SERVER_PORT = data["server_configs"]["MONGODB_PORT"]
MONGO_DB = 'LIVIS'
DEFAULT_THRESHOLD = 0.5

def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance



@singleton
class MongoHelper:
    client = None
    def __init__(self):
        if not self.client:
            self.client = MongoClient(host=MONGO_SERVER_HOST, port=MONGO_SERVER_PORT)
        self.db = self.client[MONGO_DB]

    def getDatabase(self):
        return self.db

    def getCollection(self, cname, create=False, codec_options=None, domain_override = None):
        domain = "livis"
        domain = data["username"].split("@")[1].split(".")[0]
        
        if cname == 'permissions' or cname == 'domains':
                pass
        else:
            if domain:
                cname = domain + cname

        _DB = MONGO_DB
        DB = self.client[_DB]
        # if cname in MONGO_COLLECTIONS:
        #     if codec_options:
        #         return DB.get_collection(MONGO_COLLECTIONS[cname], codec_options=codec_options)
        #     return DB[MONGO_COLLECTIONS[cname]]
        # else:
        return DB[cname]



font = cv2.FONT_HERSHEY_SIMPLEX
org = (50, 50)
fontScale = 1
color = (255, 0, 0)
thickness = 2
app = Flask(__name__)
cors = CORS(app)
weight_file = ""



@singleton
class CacheHelper():
    def __init__(self):
        # self.redis_cache = redis.StrictRedis(host="164.52.194.78", port="8080", db=0, socket_timeout=1)
        self.redis_cache = redis.StrictRedis(host= REDIS_HOST, port=REDIS_PORT, db=0, socket_timeout=1)
        # s.REDIS_CLIENT_HOST
        print("REDIS CACHE UP!")

    def get_redis_pipeline(self):
        return self.redis_cache.pipeline()
    
    def set_json(self, dict_obj):
        try:
            k, v = list(dict_obj.items())[0]
            v = pickle.dumps(v)
            return self.redis_cache.set(k, v)
        except redis.ConnectionError:
            return None

    def get_json(self, key):
        try:
            temp = self.redis_cache.get(key)
            #print(temp)\
            if temp:
                temp= pickle.loads(temp)
            return temp
        except redis.ConnectionError:
            return None
        return None

plc_exists =  data["inference"].get('plc', None)
if plc_exists:
    # process_flag = False
    # reject_flag = False
    # process_running = Button("192.168.1.50", 24, 0, 1)
    # emergency_button = Button("192.168.1.50", 8, 1, 0)
    output_button = Button("192.168.1.50", 23, 2, 1)
    sensor_trig = Button("192.168.1.50", 2, 0, 1)
    CacheHelper().set_json({"sensor_flag":False})

class Camera(ABC):
    def __init__(self, camera_id=None, KAFKA_BROKER_URL=None, topic=None, width = 640, height = 480 ):
        self.KAFKA_BROKER_URL = KAFKA_BROKER_URL
        self.topic = topic
        self.camera_id = camera_id
        self.cap = None
        self.frame = None
        self.width = width
        self.height = height

    @abstractmethod
    def _start(self):
        pass

    def start(self):
        # thread_list = []
        # for thread in threading.enumerate():
        #     print(type(thread.name))
        #     thread_list.append(thread.name)
        # print(thread_list)
        # if "Thread-3" not in thread_list:
            t1 = threading.Thread(target=self._start)
            t1.start()
        # else:
        #     print(threading.currentThread().getName())

    def get_frame(self):
        if self.frame is not None:
            self.frame = cv2.resize(self.frame,(self.width, self.height))
            return self.frame
        else:
            self.frame = cv2.imread('no_camera.png')
            self.frame = cv2.resize(self.frame,(self.width, self.height))
            return self.frame

class USB(Camera):
    def _start(self):
        while True:
            self.cap = cv2.VideoCapture(int(self.camera_id))
            try:
                ret, self.frame = self.cap.read()
                # return self.frame
            except:
                pass

            if self.frame is None:
                return None

class IP(Camera):
    def _start(self):
        self.ip = 'rtsp://' + self.camera_id + "/h264_ulaw.sdp"
        self.cap = cv2.VideoCapture(self.ip)
        while True:
            try:
                ret, self.frame = self.cap.read()
            # return self.frame
            except:
                pass
            if self.frame is None:
                return None

def BaumerConnect(camera_id):
    global camera
    camera = neoapi.Cam()
    camera.Connect(camera_id)
    camera.f.PixelFormat.SetString("BayerRG8")

# @singleton           
class Baumer(Camera):
    def _start(self):
        while True:
            try:
                input_frame = camera.GetImage()
                if not input_frame.IsEmpty():
                    input_frame = input_frame.GetNPArray()
                    input_frame = cv2.cvtColor(input_frame, cv2.COLOR_BAYER_RG2RGB)
                    self.frame = input_frame
            except:
                pass
             
class KafkaStream(Camera):
    def _start(self):
        consumer = KafkaConsumer(self.topic, bootstrap_servers=self.KAFKA_BROKER_URL , auto_offset_reset='latest')
        for message in consumer:
            decoded = cv2.imdecode(np.frombuffer(message.value, np.uint8), 1)
            self.frame = decoded

class NoStream(Camera):
    def _start(self):
        while True:
            self.frame = None

def inspect_call(res):
    print("Inspect call function")
    features = data["inference"]["features"]
    defects = data["inference"]["defects"]
    
    missing_features = []
    defects_found = []

    isAccepted = True
    classes_found = res.pandas().xyxy[0]['name'].tolist()
    print(classes_found)
    for class_name in classes_found:
        if class_name in defects:
            defects_found.append(class_name)
            isAccepted = False
    
    for feature in features:
        if feature not in classes_found:
            missing_features.append(feature)
            isAccepted = False
    
    colle={
                "part_id": data["inference"]["part_id"],
                "workstation_id": data["inference"]["ws_id"],
                "part_name": data["inference"]["part_name"],
                "workstation_name": data["inference"]["ws_name"],
                "captured_original_frame": None,
                "captured_original_frame_http":None,
                "captured_inference_frame": None,
                "captured_inference_frame_http":None,
                "isAccepted":isAccepted,
                "reject_reason":{"features":missing_features, "defects":defects_found},
                "feature_list": features,
                "defect_list": defects,
                "inference_start_time": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                # "inference_end_time": "",
                "operator_name": data["inference"]["username"], 
                "created_at": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
                "created_month": datetime.datetime.utcnow().month
        }
    log_collection = MongoHelper().getCollection(inspection_id+"_log")
    log_collection.insert_one(colle)

    if isAccepted and plc_exists:
        print("Part Accepted")
        output_button.write_value(1)

    if isAccepted == False and not plc_exists:
        print("PART REJECTED!!!!")
        output_button.write_value(2)

    CacheHelper().set_json({"result":{"isAccepted":isAccepted, "reject_reason":{"features":missing_features, "defects":defects_found}}})
    print({"isAccepted":isAccepted, "reject_reason":{"features":missing_features, "defects":defects_found}})

def load_model():
    global flag
    flag = False
    global model
    weight_name = "best.pt"
    if not path.exists("best.pt"):
        exp_id = data["inference"]["exp_id"]
        weight_file= "https://storage.googleapis.com/livis_datadrive/"+exp_id+"/runs/train/exp/weights/best.pt"
        weight_name = wget.download(weight_file)
    model = torch.hub.load('ultralytics/yolov5', 'custom', source = 'local', path=weight_name, force_reload=True)

def wait_for_sensor_trigger():
    if plc_exists:
        while True:
            sensor_value = sensor_trig.get_status()
            if sensor_value == 0:
                CacheHelper().set_json({"sensor_flag":False})
                break

stream_dict = data["inference"]["stream"]
camera_list = list(stream_dict.keys())

def flask_stream():

    CacheHelper().set_json({"inspect":False})
    CacheHelper().set_json({"result":""})
    global stream_present
    stream_present = True

    

    if len(camera_list) == 0:
        stream_obj = NoStream()
        stream_present = False
    
    else:
        if "USB" in camera_list[0]:
            stream_obj = USB(camera_id=stream_dict["USB"])
        
        elif "IP" in camera_list[0]:
            stream_obj = IP(camera_id=stream_dict["IP"])

        elif "GIGE-BAUMER" in camera_list[0]:
            stream_obj = Baumer(camera_id=stream_dict["GIGE-BAUMER"])

        elif "Kafka" in camera_list[0]:
            stream_obj = KafkaStream(topic=stream_dict["Kafka"], KAFKA_BROKER_URL = KAFKA_BROKER_URL)
        
        else:
            stream_obj = NoStream()
            stream_present = False
    
    stream_obj.start()
                

    while True:
        frame = stream_obj.get_frame()
        if frame is not None: 
            # process_trigger = process_running.get_status()
            # if process_trigger == 1 and process_flag == False:
            #     print(">>>>>>>> Process trigger given")
            conf = None
            # conf = CacheHelper().get_json("conf_val")
            if conf == None:
                conf = DEFAULT_THRESHOLD
            model.conf = conf
            res_img = frame
            if stream_present:
                res = model(frame)
                res_img = res.render()[0]
            inspect_trigger = CacheHelper().get_json("inspect")
            print(inspect_trigger)
            if inspect_trigger and stream_present:
                print("Now here!!!")
                CacheHelper().set_json({"inspect":False})
                t3 = threading.Thread(target=inspect_call, args=[res])
                t3.start()
                print("Inspect Trigger given")
            image_encoded = cv2.imencode('.jpeg', res_img)[1].tobytes()
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + image_encoded + b'\r\n\r\n')
        
@app.route('/')
def index():
    return Response(flask_stream(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/inspect/')
def inspect():
    print("Reached!")
    CacheHelper().set_json({"inspect": True})
    while True:
        redis_obj = CacheHelper().get_json("result")
        if redis_obj != "":
            print("Got result!")
            CacheHelper().set_json({"result": ""})
            if plc_exists:
                t2 = threading.Thread(target=wait_for_sensor_trigger)
                t2.start()
            return redis_obj

@app.route('/start_process/')
def start_process_call():
    inspection_doc = {
        "part_id" : data["inference"]["part_id"],
        "workstation_id" : data["inference"]["ws_id"],
        "plan_id" : "",
        "start_time" : datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),
        "end_time" : "",
        "shift_id" : "",
        "operator_id" : "",
        "produced_on" : datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),
        "status" : "started",
        "inference_urls" : [],
        "camera_id" : list(data["inference"]["stream"].values())[0],
        "synced":False
        }

    inspection_col = MongoHelper().getCollection('inspection')
    global inspection_id
    inspection_id = str(inspection_col.insert_one(inspection_doc).inserted_id)
    return "Success"

@app.route('/end_process/')
def end_process():
    inspection_col = MongoHelper().getCollection('inspection')
    inspection_col.update_one({"_id":inspection_id}, {"$set":{"end_time":datetime.datetime.now().strftime("%Y-%m-%d, %H:%M:%S"), "status":"completed"}})
    return "Success"

@app.route("/trigger/")
def trigger():
    if not plc_exists:
        return "-1"
    sensor_value = sensor_trig.get_status()
    sensor_flag = CacheHelper().get_json("sensor_flag")
    print(">>>>>>>>",sensor_value)
    if sensor_value == 1 and sensor_flag == False:
        CacheHelper().set_json({"sensor_flag":True})
        return "1"
    return "0"


if __name__ == "__main__":
    if "GIGE-BAUMER" in camera_list[0]:
        BaumerConnect(camera_id=stream_dict["GIGE-BAUMER"])
    load_model()
    app.run(host="0.0.0.0", port=9000)
