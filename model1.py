from os import path
import wget

import torch
import cv2

from common import *
from BL import pred_on_image, addReport

class Model:
    def __init__(self, weight_path = "best.pt",exp_id = None):
        self.weight_path = weight_path
        self.exp_id = exp_id
        self.weight_file = None
        self.model = None
        self.conf = CacheHelper().get_json("DEFAULT_THRESHOLD")
        self.res = None

    def download_weights(self):
        if not path.exists(path.basename(self.weight_path)):
            weight_url = "https://storage.googleapis.com/livis_datadrive/"+self.exp_id+"/runs/train/exp/weights/best.pt"
            self.weight_file = wget.download(weight_url)
    
    def load_model(self):
        self.download_weights()
        self.model = torch.hub.load('ultralytics_v1/yolov5', 'custom', path=self.weight_path, force_reload=True, source = 'local')
        self.model.iou = 0.5

    def set_threshold(self):
        self.conf = CacheHelper().get_json("DEFAULT_THRESHOLD")
        self.model.conf = self.conf
    
    def infer_frame(self, frame):
        self.set_threshold()
        self.res = self.model(frame)

        res_json = self.res.pandas().xyxy[0].to_json(orient = "records")
        predictions = list(eval(res_json))
        predicted_frame, features_missing, defects_found = pred_on_image(predictions=predictions, frame=frame)

        return predicted_frame, features_missing, defects_found

    def inspect(self, predicted_frame, features_missing, defects_found, image_name):
        self.save_infered_frame(predicted_frame, image_name)
        addReport(features_missing, defects_found, image_name)

    def save_infered_frame(self, infered_frame, image_name):
        save_path = "saved_images"
        raw_frame_name = "infer_name_" + str(image_name) + "_.jpg"
        cv2.imwrite(path.join(save_path, raw_frame_name), infered_frame)

exp_id = data["inference"]["exp_id"]


model1 = Model(exp_id = exp_id)
# model1.load_model()

# model2 = Model(["thread", "chamfer"], ["dent","burr"], weight_path="housing_best.pt")
# model2.load_model()