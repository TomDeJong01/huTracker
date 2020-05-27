# import the necessary packages
from picamera.array import PiRGBArray
from picamera import PiCamera

import argparse
import warnings
import datetime

import imutils
import json
import time
import cv2



# construct the argument parser and parse the arguments
from scripts.huTracker_track import ct

ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="conf.json")
args = vars(ap.parse_args())

conf = json.load(open(args["conf"]))
client = None

# initialize the huTracker and grab a reference to the raw huTracker capture
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
camera.rotation = conf["rotation"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

# allow the huTracker to warmup, then initialize the average frame, last
# uploaded timestamp, and frame motion counter
print("[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])
avg = None
motionCounter = 0
frameNr = 0
recObject = {"id": 0, "x": 0, "y": 0, "w": 0, "h": 0, "lf": 0, "tf": 0}
trackableObjects = {}
rects = []

# capture frames from the huTracker
print("running")
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    frameNr += 1
    # grab the raw NumPy array representing the image and initialize
    # the timestamp and occupied/unoccupied text
    frame = f.array
    text = "Unoccupied"

    # resize the frame, convert it to grayscale, and blur it

    frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    # if the average frame is None, initialize it
    if avg is None:
        print("[INFO] starting background model...")
        avg = gray.copy().astype("float")
        rawCapture.truncate(0)
        continue

    # accumulate the weighted average between the current frame and
    # previous frames, then compute the difference between the current
    # frame and running average
    cv2.accumulateWeighted(gray, avg, 0.5)
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

    # threshold the delta image, dilate the thresholded image to fill
    # in holes, then find contours on thresholded image
    thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)

    # loop over the contours
    for c in cnts:
        # if the contour is too small, ignore it
        if cv2.contourArea(c) < conf["min_area"]:
            continue
        # compute the bounding box for the contour, draw it on the frame,
        # and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        #own addition
        centerX = x + w/2;
        centery = y + h/2;

        cv2.rectangle(frame, (int(x + int((w/4))), int(y + (w/4))), (int(x + (w/2)), int(y + (h/2))), (0, 255, 0), 2)
        # cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

        if frameNr > recObject['lf'] + 3:
            #nieuw object
            recObject = {"id": recObject['id'] + 1, "x": x, "y": y, "w": w, "h": h, "lf": frameNr, "tf": 0}
            # yList = [y]
        else:
            # yList.append(y)
            #update object
            recObject = {"id": recObject['id'], "x": x, "y": y, "w": w, "h": h, "lf": frameNr, "tf": recObject["tf"] + 1}
        # print("frame:" + str(frameNr) +
        #       " objNr:" + str(recObject['id']) +
        #       " x:" + str(recObject['x']) +
        #       " y:" + str(recObject['y']) +
        #       " w:" + str(recObject['w']) +
        #       " h:" + str(recObject['h']) +
        #       " lf:" + str(recObject['lf']) +
        #       " tf:" + str(recObject['tf'])
        #       )
        print("frame:" + str(frameNr) + "    id:" + str(recObject['id']) + "    x:" + str(x) + "    y:"+str(y))
        rects.append((x, y, x+w, y+h))
        objects = ct.update(rects)


    # draw the text and timestamp on the frame
    # cv2.putText(frame, "Room Status: {}".format(text), (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    # check to see if the frames should be displayed to screen
    if conf["show_video"]:
        # display the security feed
        cv2.imshow("Security Feed", frame)
        key = cv2.waitKey(1) & 0xFF
        # if the `q` key is pressed, break from the lop
        if key == ord("q"):
            break
    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)
