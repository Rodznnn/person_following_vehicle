
from motor_driver import DualMotorController
from picamera2 import Picamera2, Preview
from gpiozero import Servo, DistanceSensor
from time import sleep
import numpy as np
from gpiozero.pins.pigpio import PiGPIOFactory
import time
import cv2

# Motor init
motor_pins_1 = (17, 18)  # Motor 1 pins
motor_pins_2 = (22, 27)  # Motor 2 pins
motors = DualMotorController(motor_pins_1, motor_pins_2)

# Distance sensor init
sensor = DistanceSensor(echo=5, trigger=6, max_distance = 4)

# Servo init
factory = PiGPIOFactory() # alternative PIN mode, PWM works through DMA (Direct Memory Acces), eliminates servo jitter, activated by "sudo pigpiod"
servo = Servo(19, pin_factory=factory, initial_value=0)


# Camera init
picam2 = Picamera2()
camera_config = picam2.create_preview_configuration()
picam2.configure(camera_config)
picam2.start()
time.sleep(1)

# Neural network initialization
object_classes = []
class_file_path = "/home/dawid/Desktop/inz/models/coco.names"  # names of objects detected by the model
with open(class_file_path, "rt") as file:
    object_classes = file.read().rstrip("\n").split("\n")  # storing these objects in the variable object_classes

config_file_path = "/home/dawid/Desktop/inz/models/ssd_mobilenet_v3_large_coco_2020_01_14.pbtxt"  # neural network model configuration
weights_file_path = "/home/dawid/Desktop/inz/models/frozen_inference_graph.pb"  # neural network weights

net = cv2.dnn_DetectionModel(weights_file_path, config_file_path)  # initializing the network with OpenCV DNN module
net.setInputSize(320, 320)  # set the input size to 320x320 pixels, as required by the model
net.setInputScale(1.0 / 127.5)  # normalize input data (pixel values) to fit in the range -1 to 1
net.setInputMean((127.5, 127.5, 127.5))  # set the mean value, subtracting 127.5 from each channel to improve model parameters
net.setInputSwapRB(True)  # OpenCV uses BGR, here we switch to RGB

def detect_objects(image, confidence_threshold, nms_threshold, draw_boxes=True, target_objects=[], numOfObjects = 20):
    class_ids, confidences, bounding_boxes = net.detect(image, confThreshold=confidence_threshold, nmsThreshold=nms_threshold)
    img_height, img_width, _ = image.shape
    img_center = (round(img_width / 2), round(img_height / 2))

    # If no specific objects are given, detect all classes
    if len(target_objects) == 0:
        target_objects = object_classes

    detected_objects_info = []

    # If any objects are detected
    if len(class_ids) != 0:

        for class_id, confidence, box in zip(class_ids.flatten(), confidences.flatten(), bounding_boxes):
            class_name = object_classes[class_id - 1]

            box_center = (box[0] + round(box[2] / 2), box[1] + round(box[3] / 2))  # box[0], box[1] - top left corner; box[2], box[3] - width, height
            x_distance_to_center = round((img_center[0] - box_center[0])/(img_width/2),3)
            if x_distance_to_center > 1:
                x_distance_to_center = 1
            elif x_distance_to_center < -1:
                x_distance_to_center = -1

            if len(detected_objects_info) < numOfObjects:

                if class_name in target_objects:

                    detected_objects_info.append([box, class_name, x_distance_to_center])

                    if draw_boxes:
                        cv2.rectangle(image, box, color=(0, 255, 0), thickness=2)
                        cv2.putText(image, class_name.upper(), (box[0] + 10, box[1] + 30),
                                    cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
                        cv2.putText(image, str(round(confidence * 100, 2)), (box[0] + 200, box[1] + 30),
                                    cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)
                        cv2.putText(image, str(x_distance_to_center), (box[0]+10, box[1]+60),
                                cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 255), 2)
                        cv2.circle(image, box_center,3,(0,255,0),-1)

    return image, detected_objects_info


# Desactivate distance
DIST_CONST = 15 + 20 #Distance from sensor to front of the car plus distance from toes to legs
DIST_BACK = 30 + DIST_CONST
DIST_FORW = DIST_BACK + 40

# Data acquiring array length
DATA_LEN = 10

if __name__ == "__main__":

    distance_array = []
    i = 0 #data acquiring iterator

    try:
        while True:


            image = picam2.capture_array("main")
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            result, objectInfo = detect_objects(image,0.45,0.2, target_objects="person", numOfObjects=1)

            if len(distance_array) < DATA_LEN:
                distance_array.append(round(sensor.distance * 100))
            else:
                distance_array[i] = round(sensor.distance * 100)

            distance = np.median(distance_array)

            print('Distance: ', distance, end="")

            if len(objectInfo)>0:

                if objectInfo[0][1]=="person":
                    servo.value = objectInfo[0][2]

                    if distance > DIST_FORW:
#                        print("Forward")
                        motors.motorSet("forward")
                    elif DIST_BACK <= distance <= DIST_FORW:
                        print(" ----- STOP ----- Object detected: ", objectInfo[0][1],end="")
                        motors.motorSet("hardstop")
                    elif distance < DIST_BACK:
#                        print("Backward")
                        motors.motorSet("backward")
            else:
                motors.motorSet("hardstop")

            print("")

            if i >= DATA_LEN-1:
                i = 0
            else:
                i += 1

            # Preview
#            cv2.imshow("Frame", result)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n Program stopped by user")

    finally:
        picam2.close()
        cv2.destroyAllWindows()
        motors.motorSet("hardstop")
