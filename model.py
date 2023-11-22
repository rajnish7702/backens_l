import torch
from os import path
from common import *
import wget
from BL import addReport, pred_on_image
from image_process import *
import cv2
import numpy as np

def load_model():
    # global conn
    # conn = child_conn
    weight_name = "best.pt"
    if not path.exists("best.pt"):
        exp_id = data["inference"]["exp_id"]
        weight_file= "https://storage.googleapis.com/livis_datadrive/"+exp_id+"/runs/train/exp/weights/best.pt"
        weight_name = wget.download(weight_file)
    global model
    model = torch.hub.load('ultralytics_v1/yolov5', 'custom', path=weight_name, force_reload=True, source = 'local')

# model = torch.hub.load('path/to/yolov5', 'custom', path='path/to/best.pt', source='local') 


# 'custom', path='best.pt',force_reload=True,source='local', pretrained =Flase)

# def img_col(res):
#     list(eval(res.pandas().xyxy[0]))


def infered_frame(frame):
    model.conf = CacheHelper().get_json("DEFAULT_THRESHOLD")
    original_frame = np.copy(frame)
    res =  model(frame)
    
    # res_img = res.render()[0]
    feature_list = data["inference"]["features"]
    defect_list = data["inference"]["defects"]
    
    res_json = res.pandas().xyxy[0].to_json(orient = "records")
    predictions = list(eval(res_json))

    predicted_frame, features_missing, defects_found = pred_on_image(predictions=predictions, frame=original_frame, feature_list=feature_list, defect_list=defect_list)

    return predicted_frame, features_missing, defects_found


def inspection(frame, image_name):
    # frame = pre_process(frame)
    # frame, image_name = conn.recv()
    predicted_frame, features_missing, defects_found = infered_frame(frame)
    save_infered_frame(predicted_frame, image_name)
    # res_img = post_process(res_img)
    # classes_found = res.pandas().xyxy[0]['name'].tolist()
    addReport(features_missing, defects_found, image_name)

def save_infered_frame(infered_frame, image_name):
    save_path = "saved_images"
    raw_frame_name = "infer_name_" + str(image_name) + "_.jpg"
    cv2.imwrite(os.path.join(save_path, raw_frame_name), infered_frame)

load_model()