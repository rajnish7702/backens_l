from neoapi import neoapi
import cv2

def connect(camera_id):
        try:
            camera = neoapi.Cam()
            camera.Connect(camera_id)
            camera.f.PixelFormat.SetString("BayerRG8")
        except Exception as e:
            print(e)

        while True:
            try:
                input_frame = camera.GetImage()
                if not input_frame.IsEmpty():
                    input_frame = input_frame.GetNPArray()
                    input_frame = cv2.cvtColor(input_frame, cv2.COLOR_BAYER_RG2RGB)
                    frame = input_frame
                    cv2.imwrite("frame.jpg",frame)
            except:
                frame = None

connect("192.168.1.8")