from picamera.array import PiRGBArray
from picamera import PiCamera
import requests
import argparse
import imutils
import json
import time
import cv2

# json params
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="conf.json")
args = vars(ap.parse_args())
conf = json.load(open(args["conf"]))

# init camera
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
camera.rotation = conf["rotation"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))
print("[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])
avg = None

# init application vars
frameNr = 0
lastFrame = 0
yList = []


def setLocalVars(json):
    conf["title"] = json["title"]
    conf["maxPeopleCount"] = json["maxPeopleCount"]
    conf["amountOfPresentPeople"] = json["amountOfPresentPeople"]


def getVars():
    r = requests.get(str(conf["apiUrl"]) + "area/" + str(conf["id"]))
    return r.json()


def count(action):
    requests.post(str(conf["apiUrl"]) + "area/" + str(conf["id"]) + "/"+action)
    print("print Action - " + str(action))


def countPersen(yList):
    # print(" ")
    print(yList)
    if yList[0] > yList[-1]:
        count("add")
        conf["amountOfPresentPeople"] += 1
        print("new count: " + str(conf["amountOfPresentPeople"]))
    else:
        count("remove")
        conf["amountOfPresentPeople"] -= 1
        print("new count: " + str(conf["amountOfPresentPeople"]))


for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    frameNr += 1
    frame = f.array
    frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    if avg is None:
        print("[INFO] starting background model...")
        avg = gray.copy().astype("float")
        rawCapture.truncate(0)
        continue

    cv2.accumulateWeighted(gray, avg, 0.5)
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

    thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)

    if frameNr > lastFrame + 2 and len(yList) > 1:
        countPersen(yList)
        yList = []

    for c in cnts:
        if cv2.contourArea(c) < conf["min_area"]:
            continue
        (x, y, w, h) = cv2.boundingRect(c)
        lastFrame = frameNr

        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        yList.append(y)

    if conf["show_video"]:
        cv2.imshow("Security Feed", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
    rawCapture.truncate(0)
