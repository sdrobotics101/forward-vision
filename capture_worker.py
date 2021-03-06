'''*-----------------------------------------------------------------------*---
                                                         Author: Jason Ma
                                                         Date  : Aug 01 2018
                                     vision

  File: capture_worker.py
  Desc: Continuously saves images from rpi-camera stream. These can also be
        fed directly into vision processing pipeline for detections.
---*-----------------------------------------------------------------------*'''

import os
import threading
import cv2 as cv
import numpy as np
import time

from picamera.array import PiRGBArray
from picamera import PiCamera

import utils

#image shapes (width, height) for use with opencv
RES_1944 = (2592, 1944)
RES_1080 = (1920, 1080)
RES_720 = (960, 720)
RES_480 = (640, 480)
RES_240 = (320, 240)

MIN_IMAGE_INTERVAL = 0.1

'''[cap_thread]----------------------------------------------------------------
  Capture thread to separate camera handling from processing
----------------------------------------------------------------------------'''
class cap_thread(threading.Thread):
  def __init__(self, image_size, image_dir):
    super(cap_thread, self).__init__()
    self.end_thread = False
    self.daemon = True
    self.image_size = image_size
    self.image_dir = image_dir
    self.image_full_dir = utils.gen_dir(self.image_dir)
    self.capture_started = False

    self.camera = PiCamera()
    self.camera.resolution = self.image_size
    self.camera.framerate = 30
    self.raw_capture = PiRGBArray(self.camera, size=self.image_size)
    self.stream = self.camera.capture_continuous(self.raw_capture, format="bgr", use_video_port=True)
    
    self.last_output_path = ""
    self.frame = None
    self.image_count = 0
    
    #camera settings
    self.camera.exposure_mode = 'auto'
    self.camera.meter_mode = 'average'
    self.camera.awb_mode = 'auto'
    self.camera.rotation = 0
    self.camera.hflip = False
    self.camera.vflip = False

  def callback(self, msg):
    if msg == 'end':
      self.end_thread = True

  def run(self):
    #publish the live directory for the processor to handle stream
    with open("live_dir.log", 'w') as f:
      f.write(self.image_full_dir + "\n")

      print("[cap] Thread started")
      self.capture_started = True

      last_time = time.time()
      
      for f in self.stream:
        curr_time = time.time()
        self.frame = f.array
        
        if curr_time - last_time < MIN_IMAGE_INTERVAL:
          self.raw_capture.truncate(0)
          continue

        if self.image_count % 100 == 0:
          print("[cap] t: %.3f --- count: %d --- dir: %s" % (curr_time - last_time, self.image_count, self.image_full_dir.split("/")[-1]))

        last_time = time.time()
        self.last_output_path = os.path.join(self.image_full_dir, str(self.image_count) + ".jpg")
        cv.imwrite(self.last_output_path, self.frame)
        self.raw_capture.truncate(0)
        self.image_count += 1

        if self.end_thread:
          break
    self.stream.close()
    self.raw_capture.close()
    self.camera.close()
    print("[cap] Thread stopped")