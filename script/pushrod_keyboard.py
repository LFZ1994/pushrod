#!/usr/bin/env python

from __future__ import print_function

import threading

import roslib; roslib.load_manifest('teleop_twist_keyboard')
import rospy

from  pushrod.msg import pushrod as Pushrod

import sys, select, termios, tty

msg = """
Reading from the keyboard  and Publishing to Pushrod!
---------------------------
Moving around:
y  up
h  stop
n  down
"""

moveBindings = {
        'y':{400,400},
        'n':{0,0},
    }

speedBindings={
        't':{1.1},
        'b':{0.9},
    }

class PublishThread(threading.Thread):
    def __init__(self, rate):
        super(PublishThread, self).__init__()
        self.publisher = rospy.Publisher('pushrod_cmd', Pushrod, queue_size = 1)
        self.vel = 20
        self.pos = 400
        self.condition = threading.Condition()
        self.done = False

        # Set timeout to None if rate is 0 (causes new_message to wait forever
        # for new data to publish)
        if rate != 0.0:
            self.timeout = 1.0 / rate
        else:
            self.timeout = None

        self.start()

    def update(self, vel, pos):
        self.condition.acquire()
        self.vel = vel
        self.pos = pos
        # Notify publish thread that we have a new message.
        self.condition.notify()
        self.condition.release()

    def stop(self):
        self.done = True
        self.update(0, 0)
        self.join()

    def run(self):
        pushrod = Pushrod()
        while not self.done:
            self.condition.acquire()
            # Wait for a new message or timeout.
            self.condition.wait(self.timeout)

            # Copy state into twist message.
            pushrod.position[0] = self.pos
            pushrod.position[1] = self.pos
            pushrod.position[2] = self.pos
            pushrod.position[3] = self.pos

            pushrod.velocity[0] = self.vel
            pushrod.velocity[1] = self.vel
            pushrod.velocity[2] = self.vel
            pushrod.velocity[3] = self.vel
            self.condition.release()
            self.publisher.publish(pushrod)
        # Publish stop message when thread exits.
        pushrod.velocity[0] = 0
        pushrod.velocity[1] = 0
        pushrod.velocity[2] = 0
        pushrod.velocity[3] = 0
        self.publisher.publish(pushrod)


def getKey(key_timeout):
    tty.setraw(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], key_timeout)
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key


def vels(speed, turn):
    return "currently:\tspeed %s\tturn %s " % (speed,turn)

if __name__=="__main__":
    settings = termios.tcgetattr(sys.stdin)

    rospy.init_node('pushrod_keyboard')

    speed = rospy.get_param("~speed", 20)
    position = rospy.get_param("~position", 400)
    turn = rospy.get_param("~turn", 1.0)
    repeat = rospy.get_param("~repeat_rate", 0.0)
    key_timeout = rospy.get_param("~key_timeout", 0.0)
    if key_timeout == 0.0:
        key_timeout = None

    pub_thread = PublishThread(repeat)

    pushros_pos = 400
    pushros_vel = 20

    try:
        pub_thread.update(pushros_vel, pushros_pos)

        while(1):
            key = getKey(key_timeout)
            if key == 'y':
                pushros_pos = 400
                pushros_vel = 20
            elif key == 'n':
                pushros_pos = 0  
                pushros_vel = 20      
            elif key == 'h':
                pushros_pos = 0  
                pushros_vel = 0
            elif (key == '\x03'):
                    break                  
            else:
                pushros_pos = 0
                pushros_vel = 0
            pub_thread.update(pushros_vel, pushros_pos)

    except Exception as e:
        print(e)

    finally:
        pub_thread.stop()

        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)