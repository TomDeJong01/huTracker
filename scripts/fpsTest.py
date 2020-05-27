import io
import picamera
from picamera.array import PiRGBArray
import argparse
import json
import cv2
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="conf.json")
args = vars(ap.parse_args())
conf = json.load(open(args["conf"]))

camera = picamera.PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
camera.rotation = conf["rotation"]
# rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))
stream = io.BytesIO()

for f in camera.capture_continuous(stream, format="bgr", use_video_port=True):
    frame = f.array
    print("ya")

    if conf["show_video"]:
        # display the security feed
        cv2.imshow("Security Feed", frame)
        key = cv2.waitKey(1) & 0xFF
        # if the `q` key is pressed, break from the lop
        if key == ord("q"):
            break
    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)
