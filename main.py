from flask import Flask, Response, request
from flask_cors import CORS
# from camera_service import get_infered_stream
from common import *
# from Button import Button
from datetime import datetime
# from paddleocr import PaddleOCR
# from PIL import Image
# from pyzbar import pyzbar
import cv2
# import numpy as np

# font = cv2.FONT_HERSHEY_SIMPLEX
# org = (50, 50)
# fontScale = 1
# color = (255, 0, 0)
# thickness = 2
app = Flask(__name__)
cors = CORS(app)

        
# @app.route('/')
# def index():
#     return Response(get_infered_stream(),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/inspect/')
def inspect():
    print("Inspect Trigger!")
    stream_present = CacheHelper().get_json("stream_present")
    print(stream_present)
    # if not stream_present:
    #     return {"isAccepted":None}
    CacheHelper().set_json({"inspect": True})
    return {}


@app.route('/getResult/')
def getResult():
    while True:
        redis_obj = CacheHelper().get_json("result")
        if redis_obj is not None:
            print("Got Result!")
            CacheHelper().set_json({"result": None})        
            return redis_obj

@app.route('/start_process/')
def start_process_call():
    result = getRunningStatus()
    if result["isRunning"] == True:
        return {"status":"Already started inspection"}
        
    
    inspection_count_doc = {"total":0, "accepted":0, "rejected":0, "callInspectionTrigger":False}
    inspection_count_col.insert_one(inspection_count_doc)

    inspection_doc = {
        "part_id" : data["inference"]["part_id"],
        "workstation_id" : data["inference"]["ws_id"],
        "plan_id" : "",
        "start_time" : datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),
        "end_time" : "",
        "shift_id" : "",
        "operator_id" : "",
        "produced_on" : datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),
        "status" : "started",
        "inference_urls" : [],
        "camera_id" : list(data["inference"]["stream"].values())[0],
        "synced":False
        }

    inspection_col = MongoHelper().getCollection('inspection')
    inspection_col.update_many({}, {"$set":{"status":"completed"}})
    inspection_id = str(inspection_col.insert_one(inspection_doc).inserted_id)
    CacheHelper().set_json({"inspection_id":inspection_id})
    return {"status":"success"}

@app.route('/end_process/')
def end_process():
    inspection_col = MongoHelper().getCollection('inspection')
    inspection_id = CacheHelper().get_json("inspection_id")
    inspection_col.update_one({"_id":inspection_id}, {"$set":{"end_time":datetime.now().strftime("%Y-%m-%d, %H:%M:%S"), "status":"completed"}})
    inspection_col.update_many({}, {"$set":{"status":"completed"}})
    inspection_count_col.delete_many({})
    CacheHelper().set_json({"inspection_id":None})
    return {"status":"success"}

# @app.route("/trigger/")
# def trigger():
#     if not plc_exists:
#         return "-1"
#     sensor_value = sensor_trig.get_status()
#     sensor_flag = CacheHelper().get_json("sensor_flag")
#     if sensor_value == 1 and sensor_flag == False:
#         CacheHelper().set_json({"sensor_flag":True})
#         return "1"
#     return "0"

@app.route("/getMegaReport/", methods = ['POST'])
def getMegaReport():
    target = 0

    skip = request.json['skip']
    limit = request.json['limit']
    status = request.json.get("status", "")
    from_date = request.json.get("from_date", "")
    to_date = request.json.get("to_date", "")

    if status == "Accepted":
        isAccepted = True
        target += 1
    elif status == "Rejected":
        isAccepted = False
        target += 1
    else:
        isAccepted = ""
    
    if from_date != "" and to_date != "":
        print("From and to date given")
        from_date_dt = datetime.strptime(from_date, '%Y-%m-%d %H:%M:%S')
        to_date_dt = datetime.strptime(to_date, '%Y-%m-%d %H:%M:%S')
        target += 1
        print(str(from_date_dt), str(to_date_dt))
    

    inspection_col = MongoHelper().getCollection('inspection')
    inspections = [str(i["_id"]) for i in inspection_col.find({},{"_id":1}).sort([('$natural', -1)])]
    reports = []
    for inspection in inspections:
        log_collection = MongoHelper().getCollection(inspection+"_log")
        for i in log_collection.find().sort([( '$natural', -1)]):
            check = 0
            if from_date != "" and to_date != "":
                inspection_time = datetime.strptime(i["inference_start_time"], '%Y-%m-%d %H:%M:%S')
                if from_date_dt < inspection_time < to_date_dt:
                    check += 1
            
            if isAccepted != "":
                if isAccepted == i["isAccepted"]:
                    check += 1
            
            if check == target:
                i["_id"] = str(i["_id"])
                reports.append(i)
    output = []
    if skip is not None and limit is not None:
        for items in reports[skip:skip+limit]:
            output.append(items)
    else:
        output = reports.copy()
    # print(output)
    coll={
        "data":output,
        "total":len(reports)
    }
    return coll

@app.route("/getRunningStatus/")
def getRunningStatus():
    inspection_col = MongoHelper().getCollection("inspection")
    inspection_doc = [i for i in inspection_col.find({}).sort([("$natural",-1)]).limit(1)]
    try:
        status = inspection_doc[0]["status"]
        if status == "started":
            CacheHelper().set_json({"inspection_id":str(inspection_doc[0]["_id"])})
            return {"isRunning":True}
        return {"isRunning":False}
    except:
        return {"isRunning":False}

@app.route("/getMetrics/")
def getMetrics():
    inspection_count = inspection_count_col.find_one()
    if inspection_count:
        inspection_count.pop("_id")
        callInspectionTrigger = CacheHelper().get_json("callInspectionTrigger")
        if callInspectionTrigger == True:
            CacheHelper().set_json({"callInspectionTrigger":False})
            inspection_count["callInspectionTrigger"] = True
    else:
        inspection_count = {"total":0, "accepted":0, "rejected":0, "callInspectionTrigger":False}
    return inspection_count

@app.route("/setThreshold/<threshold>/")
def setThreshold(threshold):
    CacheHelper().set_json({"DEFAULT_THRESHOLD":float(threshold)})
    return {"status":"success"}

@app.route("/getThreshold/")
def getThreshold():
    threshold = CacheHelper().get_json("DEFAULT_THRESHOLD")
    return {"threshold":threshold}

def save_ocr_barcode(raw_frame, image_name):
    save_path = "ocr_barcode"
    frame_name = str(image_name) + ".jpg"
    cv2.imwrite(os.path.join(save_path, frame_name), raw_frame)

# @app.route("/ocr/", methods = ["POST"])
# def ocr():
#     input_img = request.files.get("img", None).read()
#     if input_img:
#         npimg = np.fromstring(input_img, np.uint8)
#         img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    
#         image_name = datetime.now().strftime("%m%d%Y%H%M%S")
#         save_ocr_barcode(img, image_name)

#         ocr = PaddleOCR(use_angle_cls=True,use_gpu=False)
#         frame_path = "./ocr_barcode/"+image_name+".jpg"
#         result = ocr.ocr(frame_path, cls=True)

#         if result == []:
#             return {"response":"No text found"}

#         image = Image.open(frame_path).convert('RGB')
#         boxes = [line[0] for line in result]
#         txts1 = [line for line in result]
#         txts = []
#         for line1 in txts1:
#             for line2 in line1:
#                 txts.append(line2[1][0])
        
#         return {"response":txts}
#     return {"response":"No image"}

# @app.route("/barcode/", methods = ["POST"])
# def barcode():
#     input_img = request.files.get("img", None).read()
#     if input_img:
#         npimg = np.fromstring(input_img, np.uint8)
#         img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    
#         image_name = datetime.now().strftime("%m%d%Y%H%M%S")
#         save_ocr_barcode(img, image_name)
#         frame_path = "./ocr_barcode/"+image_name+".jpg"
#         img = cv2.imread(frame_path)
#         decoded = pyzbar.decode(img)
#         if decoded == []:
#             return {"response":"No text found"}
#         res = decoded[0].data.decode()

#         return {"response":res}
#     return {"resposne":"No image"}



def start_server():
    app.run(host="0.0.0.0", port=9000)