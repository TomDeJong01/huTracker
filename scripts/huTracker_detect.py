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
motionCounter = 0
frameNr = 0
recObject = {"id": 0, "x": 0, "y": 0, "w": 0, "h": 0, "lf": 0, "tf": 0}
lastFrame = 0
yList = []


def setLocalVars(json):
    conf["title"] = json["title"]
    conf["maxPeopleCount"] = json["maxPeopleCount"]
    conf["amountOfPresentPeople"] = json["amountOfPresentPeople"]


def getVars():
    r = requests.get(str(conf["apiUrl"]) + "area/" + str(conf["id"]))
    # print("print getVars")
    # print(r.status_code, r.reason)
    return r.json()


def count(action):
    r = requests.post(str(conf["apiUrl"]) + "area/" + str(conf["id"]) + "/"+action)
    print("print Action - " + str(action))
    # print(r.status_code, r.reason)


def countPersen(yList):
    print(" ")
    for i in range(len(yList)):
        if i + 1 != len(yList):
            if yList[i] == yList[i + 1]:
                continue
            if yList[i] < yList[i + 1]:
                count("remove")
                conf["amountOfPresentPeople"] = getVars()["amountOfPresentPeople"]
                print("new count: " + str(conf["amountOfPresentPeople"] ))
                break
            else:
                count("add")
                conf["amountOfPresentPeople"] = getVars()["amountOfPresentPeople"]
                print("new count: " + str(conf["amountOfPresentPeople"]))
                break


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
        if y == 0:
            yList = [y]
            continue
        else:
            yList.append(y)

    if conf["show_video"]:
        cv2.imshow("Security Feed", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
    rawCapture.truncate(0)
