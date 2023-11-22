from Button1 import PLC, PLC_Button
from common import *
import time

def plc_trigger():
    input_flag = False
    while True:
        input = input_sensor.get_value()
        if input == 1 and not input_flag:
            print("Trigger")
            time.sleep(INSPECTION_DELAY)
            input_flag = True
            CacheHelper().set_json({"callInspectionTrigger":True})
            CacheHelper().set_json({"inspect":True})

        if input == 0 and input_flag:
            input_flag = False
        
        isAccepted = CacheHelper().get_json("isAccepted")
        if isAccepted is not None:
            CacheHelper().set_json({"isAccepted":None})
            if isAccepted:
                output_button.set_value(1)
            else:
                output_button.set_value(2)

plc_exists = False
plc_config = data["inference"].get('plc', None)
if plc_config:
    plc_exists = True
    global input_sensor
    global output_button
    sensor = plc_config["sensor"]
    output = plc_config["output"]
    if sensor[0] == output[0]:
        plc_obj = PLC(sensor[0])
        if plc_obj.status:
            input_sensor = PLC_Button(plc_obj, int(sensor[1]), int(sensor[2]), int(sensor[3]))
            output_button = PLC_Button(plc_obj, int(output[1]), int(output[2]), int(output[3]))
            plc_trigger()
        else:
            print("Couldn't connect to PLC")
            while True:
                continue
    else:
        plc_obj1 = PLC(sensor[0])
        plc_obj2 = PLC(output[0])
        if plc_obj1.status and plc_obj2.status:
            input_sensor = PLC_Button(plc_obj1, int(sensor[1]), int(sensor[2]), int(sensor[3]))
            output_button = PLC_Button(plc_obj2, int(output[1]), int(output[2]), int(output[3]))
            plc_trigger()
        else:
            print("Couldn't connect to PLC")
            while True:
                continue

# def plc_trigger1():
#     print("Listening for trigger")
#     sensor_config = data["data_capture"]["plc"]["sensor"]
#     output_config = data["data_capture"]["plc"]["output"]

#     # Check if IP of PLCs is same
#     if sensor_config[0] == output_config[0]:
#         plc = PLC(sensor_config[0]).plc
#         sensor_trigger = Button("192.168.1.50", 2, 0, 1)
#         print(sensor_trigger)
#         # sensor_trigger = Button(plc, sensor_config[1], sensor_config[2], sensor_config[3])
#         output_button = Button(plc, output_config[1], output_config[2], output_config[3])
#     else:
#         plc1 = PLC(sensor_config[0]).plc
#         plc2 = PLC(output_config[0]).plc
#         sensor_trigger = Button(plc1, sensor_config[1], sensor_config[2], sensor_config[3])
#         output_button = Button(plc2, output_config[1], output_config[2], output_config[3])

#     sensor_flag = False
#     CacheHelper().set_json({"trigger":False})

#     while True:
#         sensor_value = sensor_trigger.get_value()
#         if sensor_value == 1 and not sensor_flag:
#             sensor_flag = True
#             CacheHelper().set_json({"trigger":True})
#         elif sensor_value == 0 and sensor_flag:
#             sensor_flag = False

