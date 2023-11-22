import cv2 as cv 

def testDevice(source):
   cap = cv.VideoCapture(source) 
   if cap is not None and cap.isOpened():
       print('\n\nCamera Index available: ', source, "\n\n")
    

testDevice(0) # no printout
testDevice(1) # prints message
testDevice(3) # prints message
testDevice(2) # prints message