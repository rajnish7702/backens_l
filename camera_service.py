from abc import ABC, abstractmethod
import threading
import cv2
# from model import  inspection, infered_frame
from neoapi import neoapi
from kafka import KafkaConsumer
import numpy as np
from common import *
import os
from datetime import datetime
# from flask import Flask, Response
# from flask_cors import CORS
from model1 import model1

model1.load_model()


class Camera(ABC):
    def __init__(self, camera_id=None, KAFKA_BROKER_URL=None, topic=None, width = 640, height = 480):
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
            t1 = threading.Thread(target=self._start)
            t1.start()

    def get_frame(self):
        self._start()
        if self.frame is not None:
            self.frame = cv2.resize(self.frame,(self.width, self.height))
            CacheHelper().set_json({"stream_present":True})
            return self.frame
        else:
            self.frame = cv2.imread('no_camera.png')
            self.frame = cv2.resize(self.frame,(self.width, self.height))
            CacheHelper().set_json({"stream_present":False})
            return self.frame

class KafkaStream(Camera):
    def _start(self):
        self.frame = None
        ws_id = data["inference"]["ws_id"]
        BOOTSTRAP_SERVERS = ["127.0.0.1:9092"]
        topic = ws_id+"_"+self.camera_id+"_i"
        topic.replace(":","")
        topic.replace(".","")
        consumer = KafkaConsumer(topic, bootstrap_servers=BOOTSTRAP_SERVERS, auto_offset_reset='latest')
        for message in consumer:
            decoded = cv2.imdecode(np.frombuffer(message.value, np.uint8), 1)
            self.frame = decoded
            break

        if self.frame is None:
            return None

class IP(Camera):
    def _start(self):
        self.ip = 'rtsp://' + self.camera_id + "/h264_ulaw.sdp"
        self.cap = cv2.VideoCapture(self.ip)
        # while True:
        try:
            ret, self.frame = self.cap.read()
        except:
            pass
        if self.frame is None:
            return None

class Baumer(Camera):
    def connect(self):
        try:
            self.camera = neoapi.Cam()
            self.camera.Connect(self.camera_id)
            self.camera.f.PixelFormat.SetString("BayerRG8")
        except Exception as e:
            print(e)
            
    def _start(self):
        # while True:
        try:
            input_frame = self.camera.GetImage()
            if not input_frame.IsEmpty():
                input_frame = input_frame.GetNPArray()
                input_frame = cv2.cvtColor(input_frame, cv2.COLOR_BAYER_RG2RGB)
                self.frame = input_frame
        except:
            self.frame = None

class NoStream(Camera):
    def _start(self):
        while True:
            self.frame = None

class VideoStream(Camera):
    def _start(self):
        cap = cv2.VideoCapture('vtest.avi')
        while cap.isOpened():
            ret, frame = cap.read()
            # if frame is read correctly ret is True
            if not ret:
                print("Can't receive frame (stream end?). Exiting ...")
                break
            self.frame = frame

stream_dict = data["inference"]["stream"]
camera_list = list(stream_dict.keys())

if len(camera_list) == 0:
    stream_obj = NoStream()
    CacheHelper().set_json({"stream_present":False})

else:
    if OPERATING_SYSTEM == "Windows":
        stream_obj = KafkaStream(camera_id=stream_dict["CAMERA_ID"])
    
    elif OPERATING_SYSTEM == "Linux":

        if "USB" in camera_list[0]:
            # camera_id=stream_dict["USB"]
            stream_obj = KafkaStream(camera_id=stream_dict["USB"])
        
        elif "IP" in camera_list[0]:
            camera_id=stream_dict["IP"]
            stream_obj = IP(camera_id=stream_dict["IP"])

        elif "GIGE-BAUMER" in camera_list[0]:
            camera_id=stream_dict["GIGE-BAUMER"]
            stream_obj = Baumer(camera_id=stream_dict["GIGE-BAUMER"])
            stream_obj.connect()

    else:
        camera_id = None
        stream_obj = NoStream()

# stream_obj.start()

# def start_stream():
#     while True:
#         raw_frame = stream_obj.get_frame()

#         if raw_frame is not None:
#             inspect_trigger = CacheHelper().get_json("inspect")
#             stream_present = CacheHelper().get_json("stream_present")
#             if inspect_trigger and stream_present:
#                 image_name = datetime.now().strftime("%m%d%Y%H%M%S")
#                 save_raw_frame(raw_frame, image_name)
#                 CacheHelper().set_json({"inspect":False})
#                 # conn.send(raw_frame, image_name)
#                 inspection(raw_frame, image_name)

# mp1 = threading.Thread(target=start_stream)
# mp1.start()

def save_raw_frame(raw_frame, image_name):
    save_path = "saved_images"
    raw_frame_name = "raw_frame_" + str(image_name) + "_.jpg"
    cv2.imwrite(os.path.join(save_path, raw_frame_name), raw_frame)


def main():
    while True:
        inspect_trigger = CacheHelper().get_json("inspect")
        
        # try:
        if inspect_trigger :
            CacheHelper().set_json({"inspect":False})
            print("Got inspect trigger")
            frame = stream_obj.get_frame()
            original_frame =  np.copy(frame)
            if original_frame is not None:
                predicted_frame, features_missing, defects_found = model1.infer_frame(original_frame)
                image_name = datetime.now().strftime("%m%d%Y%H%M%S")
                save_raw_frame(original_frame, image_name)
                t1 = threading.Thread(target=model1.inspect, args=(predicted_frame, features_missing, defects_found, image_name))
                t1.start()
            else:
                print("Here")
                return 

        # except Exception as e:
        #     print(e)

main()
            # predicted_frame = original_frame

        # image_encoded = cv2.imencode('.jpeg', predicted_frame)[1].tobytes()
        # yield (b'--frame\r\n'
        #     b'Content-Type: image/jpeg\r\n\r\n' + image_encoded + b'\r\n\r\n')


# app = Flask(__name__)
# cors = CORS(app)

        
# @app.route('/')
# def index():
#     return Response(get_infered_stream(),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')

# def start_stream_server():
#     # global conn
#     # conn = parent_conn
#     app.run(host="0.0.0.0", port=9000)

# start_stream_server()