from picamera.array import PiRGBArray
from picamera import PiCamera
import requests
import argparse
import imutils
import json
import time
import cv2

# read json params
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="conf.json")
args = vars(ap.parse_args())

local_json_file = open(args["conf"], "r")
conf = json.load(local_json_file)
local_json_file.close()

# init camera
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
camera.rotation = conf["rotation"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))
time.sleep(conf["camera_warmup_time"])


def updateJson():
    json_write = open(args["conf"], "w")
    json.dump(conf, json_write)
    json_write.close()


def register(name, maxPeopleCount):
    print("make register post")
    r = requests.post(conf["apiUrl"], json={
        "title": str(name),
        "maxPeopleCount": int(maxPeopleCount),
        "AmountOfPresentPeople": int(0)
    })
    conf["id"] = r.text.strip("\"")
    conf["title"] = name
    conf["maxPeopleCount"] = int(maxPeopleCount)
    conf["AmountOfPresentPeople"] = 0
    updateJson()


def setLocalVars(json):
    conf["title"] = json["title"]
    conf["maxPeopleCount"] = json["maxPeopleCount"]
    conf["AmountOfPresentPeople"] = json["amountOfPresentPeople"]
    updateJson()


def getVars():
    r = requests.get(conf["apiUrl"] + str(conf["id"]))
    if r.status_code == 200:
        return r.json()
    else:
        return False


def count(action):
    requests.post(conf["apiUrl"] + str(conf["id"]) + "/"+action)
    print("print Action - " + str(action))


def countPersen(yList):
    print(yList)
    if yList[0] > yList[-1]:
        count("add")
        conf["AmountOfPresentPeople"] += 1
        print("new count: " + str(conf["AmountOfPresentPeople"]))
    else:
        count("remove")
        conf["AmountOfPresentPeople"] -= 1
        print("new count: " + str(conf["AmountOfPresentPeople"]))


def mainLoop():
    # init application vars
    frame_nr = 0
    last_frame = 0
    y_list = []
    avg = None

    for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
        frame_nr += 1
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
        frame_delta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

        thresh = cv2.threshold(frame_delta, conf["delta_thresh"], 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        if frame_nr > last_frame + conf['buffer_frames'] and len(y_list) > 1:
            countPersen(y_list)
            y_list = []

        for c in cnts:
            if cv2.contourArea(c) < conf["min_area"]:
                continue
            (x, y, w, h) = cv2.boundingRect(c)
            last_frame = frame_nr

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            y_list.append(y)
            key = cv2.waitKey(1)

        if cv2.waitKey(1) & 0xFF == ord("t"):
            print("t is pressed")
        if conf["show_video"]:
            cv2.imshow("Security Feed", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                updateJson()
                break
        rawCapture.truncate(0)


if __name__ == "__main__":
    if conf["id"]:
        json_vars = getVars()
        if json_vars:
            setLocalVars(json_vars)
            mainLoop()
        else:
            print("kan geen contact maken met de database")
    else:
        print("register device")
        title = input("enter huTracker device name:")
        maxPeople = "NaN"
        while not maxPeople.isnumeric() or int(maxPeople) < 0:
            maxPeople = input("max number of people in room:")
        register(title, maxPeople)
        mainLoop()
