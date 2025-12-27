from gpiozero import Motor

class DualMotorController:
    def __init__(self, motor1_pins, motor2_pins):

        # Motors init
        self.motor1 = Motor(forward=motor1_pins[0], backward=motor1_pins[1])
        self.motor2 = Motor(forward=motor2_pins[0], backward=motor2_pins[1])

    def motorSet(self, mode):
        if mode == "forward":
            self.motor1.forward()  # Both motors forward
            self.motor2.forward()
        elif mode == "backward":
            self.motor1.backward()  # Both motors backwards
            self.motor2.backward()
        elif mode == "hardstop":
            self.motor1.stop()  # Both engines stop
            self.motor2.stop()

    def cleanup(self):
        self.motor1.close()  # Closing GPIO connection
        self.motor2.close()

