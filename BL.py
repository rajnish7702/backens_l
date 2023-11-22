from common import *
import datetime
import cv2
import numpy as np

def plot(frame ,label, p1, p2 , box_color ,thickness,txt_color):
    lw = 2
    cv2.rectangle(frame, p1, p2, box_color, thickness, lineType=cv2.LINE_AA)
    tf = max(lw - 1, 1)  # font thickness
    w, h = cv2.getTextSize(label, 0, fontScale = lw/3, thickness=tf)[0]  # text width, height
    outside = p1[1] - h - 3 >= 0  # label fits outside box
    p2 = p1[0] + w, p1[1] - h - 3 if outside else p1[1] + h + 3
    cv2.rectangle(frame, p1, p2, box_color, -1, cv2.LINE_AA)
    cv2.putText(frame, label, (p1[0], p1[1] - 2 if outside else p1[1] + h + 2), 0, lw / 3, txt_color,
                thickness=tf, lineType=cv2.LINE_AA)
    return frame

def pred_on_image(predictions , frame = None,lw = 2 ,defect_color = (0,0,255),feature_color = (0,125,0),
                    thickness = 2,defect_list = [],feature_list = [],config = None):
    # print("Pred on image!!!!!")
    box_color = feature_color
    if predictions == []:
        defects_found, features_missing, isAccepted = accept_reject([])
        return frame, features_missing, defects_found

    for _, coords in enumerate(predictions):
        # print(c_d)
        # coords = c_d
        # print(coords)
        # if coords["confidence"] > config.conf_thres: 
        label = coords["name"]
        txt_color = (255, 255, 255)
        padding = 10
        xmin = int(coords["xmin"])  #- padding
        ymin = int(coords["ymin"])
        xmax = int(coords["xmax"])# + padding
        ymax = int(coords["ymax"]) #+ padding
        p1,p2 = (xmin,ymin),(xmax,ymax)
        
        classes_found = [pred["name"] for pred in predictions]
        defects_found, features_missing, isAccepted = accept_reject(classes_found)
        
        if not isAccepted:
            box_color = defect_color

        predicted_frame = plot(frame ,label, p1, p2 , box_color = box_color ,thickness = thickness ,txt_color = txt_color)

    return predicted_frame, features_missing, defects_found

def accept_reject(classes_found):
    isAccepted = True
    defects_found = []
    features_missing = []

    feature_list = data["inference"]["features"]
    defect_list = data["inference"]["defects"]

    for class_name in classes_found:
            if class_name in defect_list:
                defects_found.append(class_name + " Found")
                isAccepted = False
    
    for feature in feature_list:
        if feature not in classes_found:
            features_missing.append(feature+" Missing")
            isAccepted = False

    return defects_found, features_missing, isAccepted

def addReport(features_missing, defects_found, image_name):
    print("in accept reject")
    inspection_id = CacheHelper().get_json("inspection_id") 
    if inspection_id is None:
        CacheHelper().set_json({"result":{"isAccepted":None, "reject_reason":{"features":[], "defects":[]}}})   
        return

    features = data["inference"]["features"]
    defects = data["inference"]["defects"]
    
    # predictions = res.pandas().xyxy[0]
    # pred_on_image(predictions=predictions, frame=frame_copy, feature_list=features, defect_list=defects)

    # missing_features = []
    # defects_found = []
    if features_missing == [] and defects_found == []:
        isAccepted = True
    else:
        isAccepted = False
    # isAccepted = True
    
    # print(">>>>>>>>",classes_found)
    # for class_name in classes_found:
    #     if class_name in defects:
    #         defects_found.append(class_name + " Found")
    #         isAccepted = False
    
    # for feature in features:
    #     if feature not in classes_found:
    #         missing_features.append(feature+" Missing")
    #         isAccepted = False

    

    raw_frame_name = "raw_frame_" + str(image_name) + "_.jpg"
    infered_frame_name = "infer_name_" + str(image_name) + "_.jpg"
    
    colle={
                "part_id": data["inference"]["part_id"],
                "workstation_id": data["inference"]["ws_id"],
                "part_name": data["inference"]["part_name"],
                "workstation_name": data["inference"]["ws_name"],
                "captured_original_frame": raw_frame_name,
                "captured_original_frame_http":"http://localhost:8989/saved_images/" + raw_frame_name,
                "captured_inference_frame": infered_frame_name,
                "captured_inference_frame_http":"http://localhost:8989/saved_images/" + infered_frame_name,
                "isAccepted":isAccepted,
                "reject_reason":{"features":features_missing, "defects":defects_found},
                "feature_list": features,
                "defect_list": defects,
                "inference_start_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                # "inference_end_time": "",
                "operator_name": data["username"], 
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d"),
                "created_month": datetime.datetime.now().month
        }
    
    log_collection = MongoHelper().getCollection(inspection_id+"_log")
    log_collection.insert_one(colle)

    inspect_count = inspection_count_col.find_one()
    inspection_count_id = inspect_count["_id"]
    total = int(inspect_count["total"]) + 1
    if isAccepted == True:
        accepted = int(inspect_count["accepted"]) + 1
        inspection_count_col.update_one({"_id":inspection_count_id}, {"$set":{"total":total, "accepted":accepted}})
        CacheHelper().set_json({"isAccepted":True})
    else:
        
        rejected = int(inspect_count["rejected"]) + 1
        inspection_count_col.update_one({"_id":inspection_count_id}, {"$set":{"total":total, "rejected":rejected}})
        CacheHelper().set_json({"isAccepted":False})

    result = {"result":{"isAccepted":isAccepted, "reject_reason":{"features":features_missing, "defects":defects_found}, "image":"http://localhost:8989/saved_images/" + infered_frame_name}}
    CacheHelper().set_json(result)
    print(result)