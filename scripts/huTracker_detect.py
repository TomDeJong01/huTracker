from picamera.array import PiRGBArray
from picamera import PiCamera
import argparse
import imutils
import json
import time
import cv2

ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="conf.json")
args = vars(ap.parse_args())
conf = json.load(open(args["conf"]))
client = None

camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
camera.rotation = conf["rotation"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))
print("[INFO] warming up...")
time.sleep(conf["camera_warmup_time"])
avg = None
motionCounter = 0
frameNr = 0
recObject = {"id": 0, "x": 0, "y": 0, "w": 0, "h": 0, "lf": 0, "tf": 0}
trackableObjects = {}
rects = []


def countPersen(yList):
    print(str(len(yList)))


for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    frameNr += 1
    frame = f.array
    text = "Unoccupied"
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

    for c in cnts:
        if cv2.contourArea(c) < conf["min_area"]:
            continue
        (x, y, w, h) = cv2.boundingRect(c)
        centery = y + h/2;

        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        if y == 0:
            continue

        if frameNr > recObject['lf'] + 3:
            #nieuw object
            if recObject['id'] == 9999:
                recObject['id'] = 1
            if len(yList) > 1:
                countPersen(yList)

            recObject = {"id": recObject['id'] + 1, "x": x, "y": y, "w": w, "h": h, "lf": frameNr, "tf": 0}
            yList = [centery]
        else:
            yList.append(centery)
            #update object
            recObject = {"id": recObject['id'], "x": x, "y": y, "w": w, "h": h, "lf": frameNr, "tf": recObject["tf"] + 1}

    if conf["show_video"]:
        cv2.imshow("Security Feed", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
    rawCapture.truncate(0)
