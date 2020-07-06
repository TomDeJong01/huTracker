from datetime import datetime
from picamera.array import PiRGBArray
from picamera import PiCamera
import requests
import argparse
import imutils
import json
import time
import cv2

ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True, help="conf.json")
args = vars(ap.parse_args())

local_json_file = open(args["conf"], "r")
conf = json.load(local_json_file)
conf["count"] = 0
conf["id"] = False
local_json_file.close()

# init camera
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
camera.rotation = conf["rotation"]  # 0 = strip ->camera = add && camera->strip = remove
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))
time.sleep(conf["camera_warmup_time"])


def update_json():
    json_write = open(args["conf"], "w")
    json.dump(conf, json_write)
    json_write.close()


def register(name, max_people):
    print("make register post")
    r = requests.post(conf["apiUrl"], json={
        "title": str(name),
        "maxPeopleCount": int(max_people),
        "AmountOfPresentPeople": int(0)
    })
    conf["id"] = r.text.strip("\"")
    conf["title"] = name
    conf["maxPeopleCount"] = int(max_people)
    conf["AmountOfPresentPeople"] = 0
    update_json()


def set_local_conf(response):
    conf["title"] = response["title"]
    conf["maxPeopleCount"] = response["maxPeopleCount"]
    conf["AmountOfPresentPeople"] = response["amountOfPresentPeople"]
    update_json()


def sync_get():
    r = requests.get(conf["apiUrl"] + str(conf["id"]))
    if r.status_code == 200:
        return r.json()
    else:
        return False


def count_persen(y_list, test_data=False, start_time=0, end_time=0):
    conf["count"] += 1
    second_half = y_list[len(y_list) // 2:]
    if len(y_list) % 2 != 0:
        first_half = y_list[0:int(len(y_list)+1) // 2]
    else:
        first_half = y_list[0:len(y_list) // 2]
    first_average = sum(first_half) / len(first_half)
    second_average = sum(second_half) / len(second_half)

    if first_average > second_average:
        requests.post(conf["apiUrl"] + str(conf["id"]) + "/add")
        conf["AmountOfPresentPeople"] += 1
        print("add - new count: " + str(conf["AmountOfPresentPeople"]))
    else:
        requests.post(conf["apiUrl"] + str(conf["id"]) + "/remove")
        conf["AmountOfPresentPeople"] -= 1
        print("remove - new count: " + str(conf["AmountOfPresentPeople"]))

    if test_data:
        print("\nsampling nr: " + str(conf["count"]) + "\n")
        print(y_list)
        print("first_avg:" + str(round(first_average)) + " second_avg:" + str(round(second_average)))
        time_ms = (end_time - start_time) / 1000000
        fps = len(y_list) / (time_ms/1000)
        print("frames: " + str(len(y_list)) + "\ttime: " + str(round(time_ms)) + " ms\tfps: " + str(fps) + "\n")
    update_json()


def main_loop():
    frame_nr = 0
    last_frame = 0
    y_list = []
    avg = None

    print("start main loop")
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
        # thresh = cv2.dilate(thresh, None, iterations=2)
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        if frame_nr > last_frame + conf['buffer_frames'] and len(y_list) > 3:
            if conf["get_test_data"]:
                count_persen(y_list, True, start_time, end_time)
            else:
                count_persen(y_list)
            y_list = []

        for c in cnts:
            if cv2.contourArea(c) < conf["min_area"]:
                continue
            (x, y, w, h) = cv2.boundingRect(c)
            last_frame = frame_nr
            y_list.append((y+y+h) / 2)
            if conf["get_test_data"]:
                if len(y_list) == 1:
                    start_time = time.time_ns()
                else:
                    end_time = time.time_ns()
            if conf["capture_img"]:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                out_default = '/home/pi/Documents/scripts/img/img_%s.jpg' % (str(datetime.now()))
                out_thresh = '/home/pi/Documents/scripts/img/thr_img_%s.jpg' % (str(datetime.now()))
                cv2.imwrite(out_thresh, thresh)
                cv2.imwrite(out_default, frame)

        if conf["show_video"]:
            if cnts:
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.imshow("default view", frame)
            if thresh.any():
                cv2.imshow("threshold view", thresh)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
        rawCapture.truncate(0)


if __name__ == "__main__":
    if conf["id"]:
        response = sync_get()
        if response:
            set_local_conf(response)
            main_loop()
        else:
            print("kan geen contact maken met de database, probeer het later nogeens")
    else:
        # print("register device")
        # title = input("enter huTracker device name:")
        # maxPeople = "NaN"
        # while not maxPeople.isnumeric() or int(maxPeople) < 0:
        #     maxPeople = input("max number of people in room:")
        register("Raspberry Pi", 10)
        main_loop()
