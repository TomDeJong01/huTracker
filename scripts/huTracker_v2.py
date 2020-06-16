import os
import numpy as np
import picamera
from picamera.array import PiMotionAnalysis

i = 0


class GestureDetector(PiMotionAnalysis):
    QUEUE_SIZE = 1  # the number of consecutive frames to analyze
    THRESHOLD = 1.0  # the minimum average motion required in either axis


    def __init__(self, camera):
        super(GestureDetector, self).__init__(camera)
        self.y_queue = np.zeros(self.QUEUE_SIZE, dtype=np.float)
        self.last_move = ''
        print(" init camera")


    def analyze(self, a, i=0):
        # Roll the queues and overwrite the first element with a new
        # mean (equivalent to pop and append, but faster)
        self.y_queue[1:] = self.y_queue[:-1]
        self.y_queue[0] = a['y'].mean()
        # Calculate the mean of both queues
        y_mean = self.y_queue.mean()
        # Convert left/up to -1, right/down to 1, and movement below
        # the threshold to 0
        y_move = (
            '' if abs(y_mean) < self.THRESHOLD else 'down'
            if y_mean < 0.0 else 'up')
        # Update the display
        movement = ('%s' % y_move).strip()
        if movement != self.last_move:
            self.last_move = movement
            if movement:
                print(movement)

with picamera.PiCamera(resolution='VGA', framerate=60) as camera:
    with GestureDetector(camera) as detector:
        print(" start")
        camera.start_recording(os.devnull, format='h264', motion_output=detector)
        i = 0
        try:
            print(" try")
            while True:
                print(str(i))
                camera.wait_recording(1)
                i += 1
        finally:
            print(" finaly stop")
            camera.stop_recording()