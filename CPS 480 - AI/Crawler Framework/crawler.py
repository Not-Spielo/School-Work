
"""
@author: Ju Shen
@email: jshen1@udayton.edu
@date: 02-16-2026
"""

from RLearning import ReinforceLearning as RL
from RLearning import State

import cv2 as cv
import numpy as np
import math as mth



class Crawler:
    def __init__(self, angle1=0, angle2=0, arm1=20, arm2=20, width=200, height=100, location=(0, 0), ground_y=300,
                 motion_unit=5, precision=1, learner=RL()):
        self.angle1 = angle1
        self.angle2 = angle2
        self.angle1_last = angle1  # record the last moment the angle, used to tell if the angle changes closer towards group
        self.angle2_last = angle2
        self.arm1 = arm1
        self.arm2 = arm2
        self.body_w = width
        self.body_h = height
        self.arm1_color = (0, 0, 255)
        self.location = location
        self.location_last = location
        self.contact = False
        self.contact_pt = (-1, -1)
        self.environment_y = ground_y
        self.motion_unit = motion_unit
        self.contact_angle_arm2 = -1  # record the moment when contact the angle of arm2
        self.precision = precision  # If both angle change, numerical solution is applied by searching
        # precision defines the step for search

        # p1, p2, p3, p4 are the four corners of the body. p1_c, ..., p6_c are the points on canvas
        self.p1_c = self.p1 = (round(location[0] - self.body_w / 2), round(location[1] - self.body_h / 2))
        self.p2_c = self.p2 = (round(location[0] + self.body_w / 2), round(location[1] - self.body_h / 2))
        self.p3_c = self.p3 = (round(location[0] + self.body_w / 2), round(location[1] + self.body_h / 2))
        self.p4_c = self.p4 = (round(location[0] - self.body_w / 2), round(location[1] + self.body_h / 2))

        # p5 is the joint between arm1 and arm2
        self.p5_c = self.p5 = (self.p2[0] + round(self.arm1 * mth.cos(self.angle1 * mth.pi / 180)),
                               self.p2[1] + round(self.arm1 * mth.sin(self.angle1 * mth.pi / 180)))

        # p6 is the end of arm2
        self.p6_c = self.p6 = (self.p5[0] + round(self.arm2 * mth.cos(self.angle2 * mth.pi / 180)),
                               self.p5[1] + round(self.arm2 * mth.sin(self.angle2 * mth.pi / 180)))

        self.x_shift = 0

        # figure out the angle between the diagonal line and line p2p3
        self.dia_angle_top = mth.atan(
            self.body_w / self.body_h) * 180 / 3.14  # constant: the angle between diagnal line and P2P3
        self.dia_angle_bot = 90.0 - self.dia_angle_top  # constant: the angle between diagal line and P3P4
        self.dia_len = mth.sqrt(mth.pow(self.body_w, 2.0) + mth.pow(self.body_h, 2.0))  # the length of p2p4
        self.angle1_against_dia = self.dia_angle_top + 90.0 - self.angle1  # this angle will be useful during ground contact

        # Reinforcement learning
        self.rl = learner

    # This function is used by geoCalculator() to find out the position of D or P4 and return the angle between diagonal line and ground to see if contact is on or off
    # - angle1: the self.angle1 or temporary angle 1 for contact checking
    # - angle2: the self.angle2 or temporary angle 2 for contact checking
    def angleChecker(self, angle1, angle2):
        # P6 is just the contact point
        self.p6 = self.contact_pt

        # The code below is to compute Trapezoid
        angle_B = self.dia_angle_top + 90.0 - angle1
        angle_C = 180.0 - angle2
        D = self.p6
        DF = self.arm2 * mth.sin(angle2 * mth.pi / 180.0)
        AE = self.dia_len * mth.sin((180.0 - angle_B) * mth.pi / 180.0)
        DH = DF - AE
        BE = self.dia_len * mth.cos((180.0 - angle_B) * mth.pi / 180.0)
        CF = self.arm2 * mth.cos(angle2 * mth.pi / 180.0)
        AH = BE + self.arm1 + CF
        AD = mth.sqrt(mth.pow(AH, 2.0) + mth.pow(DH, 2.0))

        self.A = (round(D[0] - AD), round(self.environment_y))
        BD = mth.sqrt(mth.pow(self.arm1, 2.0) + mth.pow(self.arm2, 2.0) - 2.0 * self.arm1 * self.arm2 * mth.cos(
            angle_C * mth.pi / 180.0))
        AC = mth.sqrt(mth.pow(self.dia_len, 2.0) + mth.pow(self.arm1, 2.0) - 2.0 * self.dia_len * self.arm1 * mth.cos(
            angle_B * mth.pi / 180.0))
        cosA = (mth.pow(self.dia_len, 2.0) + mth.pow(AD, 2.0) - mth.pow(BD, 2.0)) / (2.0 * self.dia_len * AD)
        sinA = mth.sqrt(1.0 - mth.pow(cosA, 2.0))
        angle_A = mth.asin(sinA) * 180.0 / mth.pi

        return angle_A, D[0] - AD  # The first parameter is the angle between diagonal line and ground
        # The second parameter is the x position of p6

    # This function is trigger if: CASE I: collision is detected, it will output the update p1, ..., p6.
    # Case II: collision/contact was already there from last moment
    # Also this function may further check if the contact is off for the current angle change
    def geoCalculator(self):
        # P6 is just the contact point
        self.p6 = self.contact_pt

        # The code below is to compute Trapezoid
        angle_B = self.angle1_against_dia
        angle_C = 180.0 - self.angle2
        D = self.p6
        DF = self.arm2 * mth.sin(self.angle2 * mth.pi / 180.0)
        AE = self.dia_len * mth.sin((180.0 - angle_B) * mth.pi / 180.0)
        DH = DF - AE
        BE = self.dia_len * mth.cos((180.0 - angle_B) * mth.pi / 180.0)
        CF = self.arm2 * mth.cos(self.angle2 * mth.pi / 180.0)
        AH = BE + self.arm1 + CF
        AD = mth.sqrt(mth.pow(AH, 2.0) + mth.pow(DH, 2.0))

        self.A = (round(D[0] - AD), round(self.environment_y))
        BD = mth.sqrt(mth.pow(self.arm1, 2.0) + mth.pow(self.arm2, 2.0) - 2.0 * self.arm1 * self.arm2 * mth.cos(
            angle_C * mth.pi / 180.0))
        AC = mth.sqrt(mth.pow(self.dia_len, 2.0) + mth.pow(self.arm1, 2.0) - 2.0 * self.dia_len * self.arm1 * mth.cos(
            angle_B * mth.pi / 180.0))
        cosA = (mth.pow(self.dia_len, 2.0) + mth.pow(AD, 2.0) - mth.pow(BD, 2.0)) / (2.0 * self.dia_len * AD)
        sinA = mth.sqrt(1.0 - mth.pow(cosA, 2.0))
        angle_A = mth.asin(sinA) * 180.0 / mth.pi

        # check if the current angles cause contact lose
        if angle_A <= self.dia_angle_bot:

            extra_angle_A = self.dia_angle_bot - angle_A  # find out how much angle the body is over rotated

            steps = round(self.motion_unit / self.precision)
            angle1_cur = self.angle1_last
            angle2_cur = self.angle2_last

            for i in range(1, steps):
                # check angle 1 first
                if self.angle1 > self.angle1_last:
                    angle1_cur += self.precision
                elif self.angle1 < self.angle1_last:
                    angle1_cur -= self.precision

                angle_A, p6_x = self.angleChecker(angle1_cur, angle2_cur)
                if angle_A <= self.dia_angle_bot:
                    break

                # check angle 2 second
                if self.angle2 > self.angle2_last:
                    angle2_cur += self.precision
                elif self.angle2 < self.angle2_last:
                    angle2_cur -= self.precision

                angle_A, p6_x = self.angleChecker(angle1_cur, angle2_cur)
                if angle_A <= self.dia_angle_bot:
                    break

            self.p6 = (round(p6_x), round(self.environment_y))

            # Re-calculate location
            self.location = (round(p6_x + self.body_w / 2.0), round(self.environment_y - self.body_h / 2.0))

            extra_angle_A = self.dia_angle_bot - angle_A  # find out how much angle the body is over rotated

            self.contact = False
        else:
            # P5
            cosD = (mth.pow(self.arm2, 2.0) + mth.pow(AD, 2.0) - mth.pow(AC, 2.0)) / (2.0 * self.arm2 * AD)
            sinD = mth.sqrt(1.0 - mth.pow(cosD, 2.0))
            C_x = self.p6[0] - self.arm2 * cosD
            C_y = self.p6[1] - self.arm2 * sinD
            self.p5 = (round(C_x), round(C_y))

            # P2
            B_x = self.A[0] + self.dia_len * cosA
            B_y = self.A[1] - self.dia_len * sinA
            self.p2 = (round(B_x), round(B_y))

            # P4
            self.p4 = self.A

            # P3
            theta_1 = angle_A - self.dia_angle_bot
            AG = self.body_w
            G_x = self.A[0] + AG * mth.cos(theta_1 * mth.pi / 180.0)
            G_y = self.A[1] - AG * mth.sin(theta_1 * mth.pi / 180.0)
            self.p3 = (round(G_x), round(G_y))

            # P1
            theta_2 = angle_A + self.dia_angle_top
            AI = self.body_h
            I_x = self.A[0] + AI * mth.cos(theta_2 * mth.pi / 180.0)
            I_y = self.A[1] - AI * mth.sin(theta_2 * mth.pi / 180.0)
            self.p1 = (round(I_x), round(I_y))

            # body center (average)
            self.location = (
            round((D[0] - AD + B_x + I_x + G_x) / 4.0), round((self.environment_y + B_y + I_y + G_y) / 4.0))

        return

    # This function is called by contactPos() to figure out angle1 value to touch the ground
    def angle1Change(self):
        a = self.arm1 + self.arm2 * mth.cos(self.angle2 * mth.pi / 180.0)
        b = self.arm2 * mth.sin(self.angle2 * mth.pi / 180.0)
        c = self.environment_y - self.p2[1]
        r = mth.sqrt(mth.pow(a, 2.0) + mth.pow(b, 2.0))
        sin_phi = b / r
        phi = mth.asin(sin_phi) * 180 / mth.pi

        # check if the angle is clock-wise change
        if self.angle1 > self.angle1_last:
            angle_contact = mth.asin(c / r) * 180 / mth.pi - phi
        else:  # counter-clock-wise change
            angle_contact = 180 - mth.asin(c / r) * 180 / mth.pi - phi

        # compute contact position
        x = self.arm1 * mth.cos(angle_contact * mth.pi / 180.0) + self.arm2 * mth.cos(
            (angle_contact + self.angle2) * mth.pi / 180.0) + self.p2[0]
        y = self.arm1 * mth.sin(angle_contact * mth.pi / 180.0) + self.arm2 * mth.sin(
            (angle_contact + self.angle2) * mth.pi / 180.0) + self.p2[1]

        if abs(y - self.environment_y) > 3:
            print("bug: contact pt wrong")
        self.contact_pt = (round(x), round(self.environment_y))

    # This function is called by contactPos() to figure out angle1 value to touch the ground
    def angle2Change(self):
        y_dis = self.environment_y - (self.p2[1] + self.arm1 * mth.sin(self.angle1 * mth.pi / 180.0))
        both_angle = mth.asin(y_dis / self.arm2) * 180 / mth.pi
        angle_contact = both_angle - self.angle1

        # check if the angle is compute from inside or outside
        if self.angle2 < self.angle2_last:  # counter-clock-wise
            angle_contact = 180 - self.angle1 * 2 - angle_contact

        # compute contact position
        x = self.arm1 * mth.cos(self.angle1 * mth.pi / 180.0) + self.arm2 * mth.cos(
            (self.angle1 + angle_contact) * mth.pi / 180.0) + self.p2[0]
        y = self.arm1 * mth.sin(self.angle1 * mth.pi / 180.0) + self.arm2 * mth.sin(
            (self.angle1 + angle_contact) * mth.pi / 180.0) + self.p2[1]
        if abs(y - self.environment_y) > 3:
            print("bug: angle 2 causes contact pt wrong")
        self.contact_pt = (round(x), round(self.environment_y))

    # This function is triggered only when state change from "not contact" to "contact". It will figure out the poition of the contact point
    def contactPos(self):

        angle1_change = self.angle1 - self.angle1_last
        angle2_change = self.angle2 - self.angle2_last

        if angle2_change == 0:  # angle1 changes only
            self.angle1Change()

        elif angle1_change == 0:  # angle 2 change only
            self.angle2Change()

        else:  # both angles change
            angle1_org = self.angle1  # record the original value of angle1
            angle2_org = self.angle2

            self.angle1 = self.angle1_last
            self.angle2 = self.angle2_last

            # gradually change angle from 1 to the change unit
            steps = int(self.motion_unit / self.precision)
            for i in range(1, steps):
                # check angle 1 first
                if angle1_org > self.angle1_last:
                    self.angle1 += self.precision
                elif angle1_org < self.angle1_last:
                    self.angle1 -= self.precision
                predict_y = self.p2[1] + self.arm1 * mth.sin(self.angle1 * mth.pi / 180) + self.arm2 * mth.sin(
                    (self.angle1 + self.angle2) * mth.pi / 180)
                if predict_y > self.environment_y:
                    self.angle1Change()
                    break

                # check angle 2 second
                if angle2_org > self.angle2_last:
                    self.angle2 += self.precision
                elif angle2_org < self.angle2_last:
                    self.angle2 -= self.precision
                predict_y = self.p2[1] + self.arm1 * mth.sin(self.angle1 * mth.pi / 180) + self.arm2 * mth.sin(
                    (self.angle1 + self.angle2) * mth.pi / 180)
                if predict_y > self.environment_y:
                    self.angle2Change()
                    break

            # Reset the angle1 and angle2 to its original values
            self.angle1 = angle1_org
            self.angle2 = angle2_org

    # This function will detect if the current state cause detection, if yes, return trues and the largest possible angle
    def collisionDetection(self):

        #print("angle1: " + str(self.angle1) + ", angle2: " + str(self.angle2))

        # if last moment the crawler did not contact the ground
        if not self.contact:
            predict_y = self.p2[1] + self.arm1 * mth.sin(self.angle1 * mth.pi / 180) + self.arm2 * mth.sin(
                (self.angle1 + self.angle2) * mth.pi / 180)

            if predict_y <= self.environment_y:  # still not contact
                self.contact = False
            else:  # This time it touch the ground
                # figure out the contact point
                self.contact = True
                self.contactPos()  # This function is called only if state changes from "non-contact" to "contact"

        else:  # last moment contact the ground
            self.geoCalculator()

    # This function is to computer P1, P2, ..., P6 as in "Non-contact" mode
    def nonContactPos(self):

        # p1, p2, p3, p4 are the four corners of the body
        self.p1 = (round(self.location[0] - self.body_w / 2), round(self.location[1] - self.body_h / 2))
        self.p2 = (round(self.location[0] + self.body_w / 2), round(self.location[1] - self.body_h / 2))
        self.p3 = (round(self.location[0] + self.body_w / 2), round(self.location[1] + self.body_h / 2))
        self.p4 = (round(self.location[0] - self.body_w / 2), round(self.location[1] + self.body_h / 2))

        # p5 is the joint between arm1 and arm2
        self.p5 = (self.p2[0] + round(self.arm1 * mth.cos(self.angle1 * mth.pi / 180)),
                   self.p2[1] + round(self.arm1 * mth.sin(self.angle1 * mth.pi / 180)))

        # p6 is the end of arm2
        self.p6 = (self.p5[0] + round(self.arm2 * mth.cos((self.angle1 + self.angle2) * mth.pi / 180)),
                   self.p5[1] + round(self.arm2 * mth.sin((self.angle1 + self.angle2) * mth.pi / 180)))

    # This function compute the actual position of the crawler
    def posConfig(self, x_shift=0, sliding_mode=False):

        self.x_shift = x_shift

        # Only configure the crawler if angle 1 or angle 2 changes
        if (self.angle1 != self.angle1_last) or (self.angle2_last != self.angle2):

            # Record the moment of cotact the angle of arm1 against diagonal line because later this is constant during contact movement
            self.angle1_against_dia = self.dia_angle_top + 90.0 - self.angle1

            # check if the second arm touch the ground
            self.collisionDetection()

            # If the crawler does not touch the ground
            if (not self.contact):
                # The body is leveled
                self.nonContactPos()

            # The crawler touch the ground
            else:

                self.geoCalculator()  # let this function figure out the new values of p1, p2, ... , p6

                # if the geoCalculator() finds out contact lost, recalculate p1, ..., p6 as non-contact situation
                if not self.contact:
                    self.nonContactPos()

            #print('location: ' + str(self.location))

            # At the end reset the status of angle 1 and angle 2
            self.angle1_last = self.angle1
            self.angle2_last = self.angle2
            self.location_last = self.location



    # A function to draw the crawler position on the screen
    # the second parameter is used for screen shifting purpose
    def draw(self, canvas):

        # update canvas coordinates of points
        self.p1_c = (round(self.p1[0] + self.x_shift), round(self.p1[1]))
        self.p2_c = (round(self.p2[0] + self.x_shift), round(self.p2[1]))
        self.p3_c = (round(self.p3[0] + self.x_shift), round(self.p3[1]))
        self.p4_c = (round(self.p4[0] + self.x_shift), round(self.p4[1]))
        self.p5_c = (round(self.p5[0] + self.x_shift), round(self.p5[1]))
        self.p6_c = (round(self.p6[0] + self.x_shift), round(self.p6[1]))

        # draw the body
        contours = np.array([self.p1_c, self.p2_c, self.p3_c, self.p4_c])
        # contours = np.array([int(self.p1), int(self.p2), int(self.p3), int(self.p4)])
        cv.line(canvas, self.p1_c, self.p2_c, (50, 50, 50), 2, cv.LINE_AA)
        cv.line(canvas, self.p2_c, self.p3_c, (50, 50, 50), 2, cv.LINE_AA)
        cv.line(canvas, self.p3_c, self.p4_c, (50, 50, 50), 2, cv.LINE_AA)
        cv.line(canvas, self.p4_c, self.p1_c, (50, 50, 50), 2, cv.LINE_AA)
        cv.fillPoly(canvas, pts=[contours], color=(50, 50, 50))

        # draw first arm
        cv.line(canvas, self.p2_c, self.p5_c, (0, 0, 230), 4, cv.LINE_AA)

        # draw second arm
        cv.line(canvas, self.p5_c, self.p6_c, (0, 200, 50), 4, cv.LINE_AA)

        # print('location: ' + str(self.location))
        # print('p1_c: ' + str(self.p1_c) + ', p1: ' + str(self.p1))
        # print('p2_c: ' + str(self.p2_c) + ', p2: ' + str(self.p2))
        # print('p3_c: ' + str(self.p3_c) + ', p3: ' + str(self.p3))
        # print('p4_c: ' + str(self.p4_c) + ', p4: ' + str(self.p4))
        # if self.contact:
        #     cv.circle(canvas, self.p6, 2, (255, 0, 0), 2)
        #     cv.circle(canvas, self.contact_pt, 2, (0, 255, 0), 2)
        #     cv.circle(canvas, self.A, 2, (0, 0, 255), 2)


# Button class for canvas
class Button:
    def __init__(self, width, height, x, y, margin_ratio=0.2, text1='', text2='', clicked_color=(50, 50, 200), gap=0, type=0, selected=False):

        self.width = width
        self.height = height
        self.top_left = (int(x), int(y))
        self.bot_right = (int(x + width), int(y + height))
        self.text_pos = (int(x + width * margin_ratio), int(y + height * .7))
        self.org_color = (80, 150, 50)
        self.over_color = (100, 190, 100) # the button color that the mouse is entering its region
        self.clicked_color = clicked_color
        self.org_txt_color = (255, 255, 255)
        self.over_txt_color = (255, 255, 255)
        self.over = False # If the mouse enter the region
        self.clicked = False # If the button is down
        self.text = text1
        self.text2 = text2
        self.type = type

        # For radio button use
        self.gap = gap
        self.selected = selected

        if type == 1:
            self.top_left = (int(x + width/1.5), int(y))
            self.bot_right = (int(x + (1.2 + self.gap - 0.5) * width ), int(y + height))


        if type == 3:
            self.top_left = (int(x), int(y))
            self.bot_right = (int(x + width), int(y + height))

            self.text_pos = (int(x), int(y + height * .7))
            self.check_box_len = height *.6

            # check box corner
            self.check_box_p1 = (int(self.bot_right[0] - self.check_box_len * .4), int(self.top_left[1] + self.check_box_len * .5))
            self.check_box_p2 = (int(self.bot_right[0] + self.check_box_len * .6), int(self.top_left[1] + self.check_box_len * 1.5))

            # check box tick
            self.tick_p1 = (int(self.check_box_p1[0]), int((self.check_box_p1[1] * .5 + self.check_box_p2[1] * .5)))
            self.tick_p2 = (int(self.check_box_p1[0] * .5 + self.check_box_p2[0] * .5), int(self.check_box_p1[1] * .2 + self.check_box_p2[1] * .8))
            self.tick_p3 = (int(self.check_box_p2[0]), int(self.check_box_p1[1]))

    def draw(self, img):
        if self.type == 0:
            if self.clicked:
                cv.rectangle(img, self.top_left, self.bot_right, self.clicked_color, -1)
                cv.putText(img, self.text2, self.text_pos, 4, 1.2, self.org_txt_color, 2, cv.LINE_AA)
                cv.line(img, (int(self.top_left[0]), int(self.top_left[1])), (int(self.top_left[0]), int(self.bot_right[1])), (0, 0, 0), 2)
                cv.line(img, (int(self.top_left[0]), int(self.top_left[1])), (int(self.bot_right[0]), int(self.top_left[1])), (0, 0, 0), 2)
            elif self.over:
                cv.rectangle(img, self.top_left, self.bot_right, self.over_color, -1)
                cv.putText(img, self.text, self.text_pos, 4, 1.2, self.over_txt_color, 2, cv.LINE_AA)
                cv.line(img, (int(self.top_left[0]), int(self.bot_right[1])), (int(self.bot_right[0]), int(self.bot_right[1])), (0, 0, 0), 2)
                cv.line(img, (int(self.bot_right[0]), int(self.top_left[1])), (int(self.bot_right[0]), int(self.bot_right[1])), (0, 0, 0), 2)
            else:
                cv.rectangle(img, self.top_left, self.bot_right, self.org_color, -1)
                cv.putText(img, self.text, self.text_pos, 4, 1.2, self.org_txt_color, 2, cv.LINE_AA)
                cv.line(img, (int(self.top_left[0]), int(self.bot_right[1])), (int(self.bot_right[0]), int(self.bot_right[1])), (0, 0, 0), 2)
                cv.line(img, (int(self.bot_right[0]), int(self.top_left[1])), (int(self.bot_right[0]), int(self.bot_right[1])), (0, 0, 0), 2)

        elif self.type == 1: #radio buttons for learning options
            cv.putText(img, self.text, self.text_pos, 3, 1.0, (100, 100, 100), 2, cv.LINE_AA)
            cv.circle(img, (int(self.text_pos[0] + self.width * self.gap), int(self.text_pos[1] - self.height/6)), 15, (50, 50, 50), 2)


            if self.selected:
                cv.circle(img, (int(self.text_pos[0] + self.width * self.gap), int(self.text_pos[1] - self.height/6)), 8, (50, 150, 50), -1)


        elif self.type == 2:  # radio buttons for zoom
            cv.putText(img, self.text, self.text_pos, 3, 1.0, (50, 50, 50), 2, cv.LINE_AA)
            cv.circle(img, (int(self.text_pos[0] + self.width * self.gap), int(self.text_pos[1] - self.height / 6)), 15,
                      (250, 250, 250), -1)
            cv.circle(img, (int(self.text_pos[0] + self.width * self.gap), int(self.text_pos[1] - self.height / 6)), 15,
                      (50, 50, 50), 2)
            # cv.rectangle(img, self.top_left, self.bot_right, (50, 100, 100), 2)


            if self.selected:
                cv.circle(img, (int(self.text_pos[0] + self.width * self.gap), int(self.text_pos[1] - self.height / 6)),
                          8, (50, 150, 50), -1)


        elif self.type == 3:  # radio buttons for zoom
            cv.putText(img, self.text, self.text_pos, 3, 1.0, (50, 50, 50), 2, cv.LINE_AA)
            cv.rectangle(img, self.check_box_p1, self.check_box_p2, (250, 250, 250), -1)
            cv.line(img, self.check_box_p1, (self.check_box_p2[0], self.check_box_p1[1]), (0, 0, 0), 2)
            cv.line(img, self.check_box_p1, (self.check_box_p1[0], self.check_box_p2[1]), (0, 0, 0), 2)


            if self.selected:
                cv.line(img, self.tick_p1, self.tick_p2, (50, 150, 50), 5)
                cv.line(img, self.tick_p2, self.tick_p3, (50, 150, 50), 5)

# The environment that will interact the crawler
class Environment:
    def __init__(self, crawler=Crawler(), width=2000, height=1500, scale=1.0):
        self.canvas_w = width
        self.canvas_h = height
        self.scale = scale
        self.ground_y = height / 3
        self.crawler = crawler
        self.img = np.zeros((self.canvas_h, self.canvas_w, 3), dtype=np.uint8)
        self.crawler.environment_y = self.ground_y

        # for drawing coordinate use
        self.font = cv.FONT_HERSHEY_SIMPLEX
        self.unit = self.canvas_w / 10

        # for sliding canvas uses
        self.x_shift = 0  # represent the x shift around campus
        self.slide_speed = self.unit * 0.1
        self.slide_size = self.unit * 4 / self.slide_speed
        self.slide_counter = 0
        self.sliding_mode = False  # true: currently slide the window  # false: the window is still
        self.min_idx = 0  # the smallest number of coordinate shown on canvas
        self.max_idx = 9  # the largest number of coordinate shown on canvas
        self.min_pos = 0 # the smallest number position on canvas
        self.max_pos = self.min_pos + (self.max_idx - self.min_idx) * self.unit
        self.play_mode = False # see how the crawler moves to learn (one iteration at a time)

        # for drawing buttons use
        self.play_btn = Button(width=self.canvas_w/12, height=self.canvas_h/25, x=self.canvas_w/30, y=self.canvas_h/40, margin_ratio=0.2, text1='play', text2='stop..')
        self.learning_btn = Button(width=self.canvas_w/5, height=self.canvas_h/25, x=self.canvas_w/6, y=self.canvas_h/40, margin_ratio=0.05, text1='Learn 50000 steps', text2='Learning...Wait...')
        self.reset_btn = Button(width=self.canvas_w/12, height=self.canvas_h/25, x=self.canvas_w/2.5, y=self.canvas_h/40, margin_ratio=0.2, text1='reset', text2='reset', clicked_color=(0, 0, 0))
        self.draw_btns = False
        self.btn_counter = 0
        self.option_learning_btns = []
        self.option_zoom_ranges = []
        self.option_zoom_scale = []

        mc_btn = Button(width=self.canvas_w/5, height=self.canvas_h/25, x=self.canvas_w/2.5, y=self.canvas_h/40, margin_ratio=0.6, text1='Monte Carlo', text2='---', gap=0.6, type=1, selected=True)
        sarsa_btn = Button(width=self.canvas_w/5, height=self.canvas_h/25, x=self.canvas_w/1.75, y=self.canvas_h/40, margin_ratio=0.6, text1='TD SARSA', text2='---', gap=0.49, type=1)
        q_btn = Button(width=self.canvas_w/5, height=self.canvas_h/25, x=self.canvas_w/1.4, y=self.canvas_h/40, margin_ratio=0.6, text1='Q-learning', text2='---', gap=0.55, type=1)

        zoom_range1_btn = Button(width=self.canvas_w/18, height=self.canvas_h/25, x=self.canvas_w * 0.03, y=self.canvas_h * 0.82, margin_ratio=0, text1='2x2', text2='---', gap=0.8, type=2, selected=True)
        zoom_range2_btn = Button(width=self.canvas_w / 18, height=self.canvas_h / 25, x=self.canvas_w * 0.03, y=self.canvas_h * 0.87, margin_ratio=0, text1='3x3', text2='---', gap=0.8, type=2)
        zoom_range3_btn = Button(width=self.canvas_w / 18, height=self.canvas_h / 25, x=self.canvas_w * 0.03, y=self.canvas_h * 0.92, margin_ratio=0, text1='5x5', text2='---', gap=0.8, type=2)

        zoom_scale1_btn = Button(width=self.canvas_w / 20, height=self.canvas_h / 25, x=self.canvas_w * 0.12,
                                 y=self.canvas_h * 0.82, margin_ratio=0, text1='1x', text2='---', gap=0.7, type=2, selected=True)
        zoom_scale2_btn = Button(width=self.canvas_w / 20, height=self.canvas_h / 25, x=self.canvas_w * 0.12,
                                 y=self.canvas_h * 0.87, margin_ratio=0, text1='2x', text2='---', gap=0.7, type=2)
        zoom_scale3_btn = Button(width=self.canvas_w / 20, height=self.canvas_h / 25, x=self.canvas_w * 0.12,
                                 y=self.canvas_h * 0.92, margin_ratio=0, text1='3x', text2='---', gap=0.7, type=2)

        self.show_analysis_btn = Button(width=self.canvas_w / 5, height=self.canvas_h / 25, x=self.canvas_w * .01, y=self.canvas_h * .4,
                        margin_ratio=0.6, text1='Show analysis panels', text2='---', gap=1, type=3, selected=True)

        self.option_learning_btns.append(mc_btn)
        self.option_learning_btns.append((sarsa_btn))
        self.option_learning_btns.append(q_btn)

        self.option_zoom_ranges.append(zoom_range1_btn)
        self.option_zoom_ranges.append(zoom_range2_btn)
        self.option_zoom_ranges.append(zoom_range3_btn)

        self.option_zoom_scale.append(zoom_scale1_btn)
        self.option_zoom_scale.append(zoom_scale2_btn)
        self.option_zoom_scale.append(zoom_scale3_btn)

        # for drawing state value uses
        self.state_plot_tl = (int(self.canvas_w * 0.35), int(self.canvas_h * 0.47)) # top left corner on canvas
        self.state_plot_br = (int(self.canvas_w * 0.95), int(self.canvas_h * 0.92)) # bottom right corner on canvas
        self.angle_1_label_pos = (int(self.state_plot_tl[0] - self.canvas_w * 0.03), int(self.state_plot_br[1] - self.canvas_h * 0.08)) # top left corner on canvas
        self.angle_2_label_pos = (int(self.state_plot_br[0] - 0.06 * self.canvas_w), int(self.state_plot_tl[1] - self.canvas_h * 0.01)) # top left corner on canvas
        self.state_img = np.zeros((self.state_plot_br[1] - self.state_plot_tl[1], self.state_plot_br[0] - self.state_plot_tl[0], 3), dtype=np.uint8)
        self.state_unit_w = (self.state_plot_br[0] - self.state_plot_tl[0])/self.crawler.rl.cols
        self.state_unit_h = (self.state_plot_br[1] - self.state_plot_tl[1])/self.crawler.rl.rows
        self.redraw_state = True
        self.angle_1_img = np.zeros((int(self.canvas_h * 0.035), int(self.canvas_w * 0.06), 3), dtype=np.uint8)
        self.angle_1_img[:] = (200, 200, 200)
        cv.putText(self.angle_1_img, 'Angle 1', (int(2), int(35)), self.font, 1.0, (0, 0, 250), 2, cv.LINE_AA)
        self.angle_1_img = cv.rotate(self.angle_1_img, cv.ROTATE_90_COUNTERCLOCKWISE)
        self.dragging_state = False
        self.scale_tl = False
        self.scale_tr = False
        self.scale_bl = False
        self.scale_br = False
        self.unit_tl = (int((0 - self.crawler.rl.angle1_range[0]) * self.state_unit_h), int((0 - self.crawler.rl.angle2_range[0]) * self.state_unit_w)) # the hightlighted square of current state

        # for drawing Q-value uses
        self.q_plot_tl = (int(self.canvas_w * 0.02), int(self.canvas_h * 0.47))  # top left corner on canvas
        self.q_plot_br = (int(self.canvas_w * 0.28), int(self.canvas_h * 0.72))  # bottom right corner on canvas
        self.dragging_Q = False
        self.drawQ = False
        self.cur_j = 0 # the current highlighted state
        self.cur_i = 0

        # for zoom effect uses
        self.zoom_effect = False
        self.zoom_pos = (-1, -1)
        self.zoom_range = 1 # from mouse position, counter zoom_range number forward and backward
        self.zoom_scale = 1
        self.zoom_backup = self.img.copy()
        self.zoom_r = 0
        self.zoom_c = 0

        # Q-learning or MC: (0-MC, 2-Bellman)
        self.play_option = 0

        # Show the analaysis panel
        self.show_analysis = True
        self.show_refresh = False

        self.mouse_over_Q = False

    def drawQpanel(self):
        self.img[self.q_plot_tl[1]:self.q_plot_br[1], self.q_plot_tl[0]:self.q_plot_br[0]] = (0, 0, 0)

        # The frame
        cv.line(self.img, self.q_plot_tl, (self.q_plot_br[0], self.q_plot_tl[1]), (0, 255, 0), 3, cv.LINE_AA)
        cv.line(self.img, (self.q_plot_tl[0], self.q_plot_br[1]), self.q_plot_br, (0, 255, 0), 3, cv.LINE_AA)
        cv.line(self.img, self.q_plot_tl, (self.q_plot_tl[0], self.q_plot_br[1]), (0, 255, 0), 3, cv.LINE_AA)
        cv.line(self.img, (self.q_plot_br[0], self.q_plot_tl[1]), self.q_plot_br, (0, 255, 0), 3, cv.LINE_AA)

        # Put Text
        text = 'Q(' + str(f"{self.crawler.angle1:02d}") + ', ' + str(f"{self.crawler.angle2:02d}") + ')'
        r = int((self.crawler.angle1 - self.crawler.rl.angle1_range[0])/5)
        c = int((self.crawler.angle2 - self.crawler.rl.angle2_range[0])/5)
        if self.zoom_effect:
            angle_1 = self.crawler.rl.angle1_range[0] + 5 * self.zoom_r
            angle_2 = self.crawler.rl.angle2_range[0] + 5 * self.zoom_c
            r = int(self.zoom_r)
            c = int(self.zoom_c)
            text = 'Q(' + str(f"{angle_1:02d}") + ', ' + str(f"{angle_2:02d}") + ')'

        cv.putText(self.img, text, (int(self.q_plot_tl[0] + (self.q_plot_br[0] - self.q_plot_tl[0]) * 0.08), int(self.q_plot_tl[1] + (self.q_plot_br[1] - self.q_plot_tl[1]) * 0.13)), 4, 1.2, (50, 255, 255), 2, cv.LINE_AA)

        # Draw 9 Q-values frame
        x1 = int(self.q_plot_tl[0] + (self.q_plot_br[0] - self.q_plot_tl[0]) * 0.08)
        y1 = int(self.q_plot_tl[1] + (self.q_plot_br[1] - self.q_plot_tl[1]) * 0.2)
        x2 = int(self.q_plot_br[0] - (self.q_plot_br[0] - self.q_plot_tl[0]) * 0.08)
        y2 = y1
        x3 = x2
        y3 = int(self.q_plot_br[1] - (self.q_plot_br[1] - self.q_plot_tl[1]) * 0.08)
        x4 = x1
        y4 = y3
        x_step = int((x2 - x1) / 3)
        y_step = int ((y4 - y1) / 3)


        for j in range(3):
            for i in range(3):
                val = str(f"{self.crawler.rl.Qvalue[r][9 * c + 3 * j + i]:.1f}")
                tl = (int(x1 + i * x_step), int(y1 + j * y_step))
                br = (int(tl[0] + x_step), int(tl[1] + y_step))
                txt_pos = (int(tl[0] + 0.2 * (br[0] - tl[0])), int(tl[1] + 0.6 * (br[1] - tl[1])))
                cv.putText(self.img, val, txt_pos, 4, 1, (200, 200, 200), 2, cv.LINE_AA)
                cv.rectangle(self.img, tl, br, (0, 255, 255), 1)



    # Recturn the Q values
    def getQvalues(self, x1, y1, x2, y2, i, j, val):
        sub_w = (x2 - x1)/3
        sub_h = (y2 - y1)/3

        a = self.crawler.rl.Qvalue[j].index(max(self.crawler.rl.Qvalue[j][9 * i:9 * i + 9])) - (9 * i)
        angle1_update = angle2_update = 0

        if a == 0:
            angle1_update = -1
            angle2_update = -1
        elif a == 1:
            angle1_update = -1
            angle2_update = 0
        elif a == 2:
            angle1_update = -1
            angle2_update = 1
        elif a == 3:
            angle1_update = 0
            angle2_update = -1
        elif a == 4:
            angle1_update = 0
            angle2_update = 0
        elif a == 5:
            angle1_update = 0
            angle2_update = 1
        elif a == 6:
            angle1_update = 1
            angle2_update = -1
        elif a == 7:
            angle1_update = 1
            angle2_update = 0
        else:
            angle1_update = 1
            angle2_update = 1

        cur_y = (1 + angle1_update) * sub_h + y1
        cur_x = (1 + angle2_update) * sub_w + x1

        self.state_img[int(cur_y):int(cur_y + sub_h), int(cur_x):int(cur_x + sub_h)] = (0, 200, 0)
        return


    # draw the state values
    def drawStates(self):
        # print('rows: ' + str(self.crawler.rl.rows) + ', cols: ' + str(self.crawler.rl.cols))
        # print('Q(' + str(len(self.crawler.rl.Qvalue)) + ', ' + str(len(self.crawler.rl.Qvalue[0])) + ')')
        # print('R(' + str(len(self.crawler.rl.R)) + ', ' + str(len(self.crawler.rl.R[0])) + ')')
        # print('PI(' + str(len(self.crawler.rl.pi)) + ', ' + str(len(self.crawler.rl.pi[0])) + ')')

        # Draw Q-values
        #
        # max_Q = np.amax(self.crawler.rl.Qvalue)
        # min_Q = np.amin(self.crawler.rl.Qvalue)


        # Re-render the sub-images
        if self.redraw_state:
            for j in range(0, self.crawler.rl.rows):
                cur_y = int(self.state_unit_h * j)
                cur_y_end = int(cur_y + self.state_unit_h)
                for i in range(0, self.crawler.rl.cols):
                    cur_x = int(self.state_unit_w * i)
                    cur_x_end = int(cur_x + self.state_unit_w)
                    val = int(max(self.crawler.rl.Qvalue[j][i * 9:i * 9 + 9]))

                    if self.drawQ:
                        self.state_img[cur_y:cur_y_end, cur_x:cur_x_end] = (0, 0, 0)
                        self.getQvalues(cur_x, cur_y, cur_x_end, cur_y_end, i, j, val)
                    else:
                        if val * 2 > 255:
                            val = 255
                        else:
                            val *= 2
                        self.state_img[cur_y:cur_y_end, cur_x:cur_x_end] = (val, 0, 0)


            # Draw the grid
            for j in range(1, self.crawler.rl.rows):
                cur_y = int(self.state_unit_h * j)
                cv.line(self.state_img, (0, cur_y), (self.state_img.shape[1]-1, cur_y), (150, 150, 150), 1, cv.LINE_AA)
            for i in range(1, self.crawler.rl.cols):
                cur_x = int(self.state_unit_w * i)
                cv.line(self.state_img, (cur_x, 0), (cur_x, self.state_img.shape[0]-1), (150, 150, 150), 1, cv.LINE_AA)


            # At the end turn it off
            self.redraw_state = False


        # clear last state
        unit_br = (int(self.unit_tl[0] + self.state_unit_w), int(self.unit_tl[1] + self.state_unit_h))
        cv.rectangle(self.state_img, self.unit_tl, unit_br, (0, 0, 0), 3)
        cv.rectangle(self.state_img, self.unit_tl, unit_br, (150, 150, 150), 1)

        # Draw the updated current state
        self.cur_j = (self.crawler.angle1 - self.crawler.rl.angle1_range[0]) / self.crawler.motion_unit
        self.cur_i = (self.crawler.angle2 - self.crawler.rl.angle2_range[0]) / self.crawler.motion_unit
        self.unit_tl = (int(self.state_unit_w * self.cur_i), int(self.state_unit_h * self.cur_j))
        unit_br = (int(self.unit_tl[0] + self.state_unit_w), int(self.unit_tl[1] + self.state_unit_h))

        if self.drawQ:
            cv.rectangle(self.state_img, self.unit_tl, unit_br, (0, 0, 255), 8)
        else:
            cv.rectangle(self.state_img, self.unit_tl, unit_br, (0, 255, 255), 3)


        # Copy sub-image to canvas
        self.img[self.state_plot_tl[1]:self.state_plot_br[1], self.state_plot_tl[0]:self.state_plot_br[0]] = self.state_img[0:self.state_img.shape[0], 0:self.state_img.shape[1]]




        # The frames around the states
        cv.line(self.img, self.state_plot_tl, (self.state_plot_br[0], self.state_plot_tl[1]), (0, 255, 0), 5, cv.LINE_AA)
        cv.line(self.img, (self.state_plot_tl[0], self.state_plot_br[1]), self.state_plot_br, (0, 255, 0), 4, cv.LINE_AA)
        cv.line(self.img, self.state_plot_tl, (self.state_plot_tl[0], self.state_plot_br[1]), (0, 0, 255), 5, cv.LINE_AA)
        cv.line(self.img, (self.state_plot_br[0], self.state_plot_tl[1]), self.state_plot_br, (0, 0, 255), 4, cv.LINE_AA)


        # Draw the angles label
        cv.putText(self.img, 'Angle 2', self.angle_2_label_pos, self.font, 1.0, (0, 100, 0), 2, cv.LINE_AA)
        if int(self.angle_1_label_pos[0]) >= 0:
            self.img[int(self.angle_1_label_pos[1]):int(self.angle_1_label_pos[1]+self.angle_1_img.shape[0]), int(self.angle_1_label_pos[0]):int(self.angle_1_label_pos[0] + self.angle_1_img.shape[1])] = self.angle_1_img[:]

        # Coordinate highlight
        r, c, angle_1, angle_2 = 0, 0, 0, 0
        if self.zoom_effect and not self.dragging_state:
            angle_1 = self.crawler.rl.angle1_range[0] + 5 * self.zoom_r
            angle_2 = self.crawler.rl.angle2_range[0] + 5 * self.zoom_c
            r = int(self.zoom_r)
            c = int(self.zoom_c)
        else:
            angle_1 = self.crawler.angle1
            angle_2 = self.crawler.angle2
            r = self.cur_j
            c = self.cur_i

        seg_1 = (self.state_plot_br[1] - self.state_plot_tl[1]) / self.crawler.rl.rows
        seg_2 = (self.state_plot_br[0] - self.state_plot_tl[0]) / self.crawler.rl.cols
        seg_1_int = int(seg_1)
        seg_2_int = int(seg_2)

        # angle 1
        p1 = (int(self.state_plot_tl[0] + c * seg_2), self.state_plot_tl[1])
        p2 = (p1[0] + seg_2_int, self.state_plot_tl[1])
        pos1 = (int(p1[0]), int(p1[1] - seg_2 / 2.0))

        # angle 2
        p3 = (self.state_plot_tl[0], int(self.state_plot_tl[1] + r * seg_1))
        p4 = (self.state_plot_tl[0], p3[1] + seg_1_int)
        pos2 = (int(p3[0] - seg_1 * 1.2), p4[1])
        if angle_1 < 0:
            pos2 = (int(p3[0] - seg_1 * 1.8), p4[1])


        cv.line(self.img, p1, p2, (0, 255, 0), 15, cv.LINE_AA)
        cv.line(self.img, p3, p4, (0, 0, 255), 15, cv.LINE_AA)
        cv.putText(self.img, str(angle_2), pos1, self.font, 0.8, (0, 100, 0), 2, cv.LINE_AA)
        cv.putText(self.img, str(angle_1), pos2, self.font, 0.8, (0, 0, 255), 2, cv.LINE_AA)

        # Make a back for later zoom uses
        self.zoom_backup = self.img.copy()

        # Draw Zoom effect
        if self.zoom_effect and not self.dragging_state:
            lef_x = int(self.zoom_pos[0] - self.state_unit_w * self.zoom_range)
            if lef_x < 0:
                lef_x = 0

            rig_x = int(self.zoom_pos[0] + self.state_unit_w * self.zoom_range)
            top_y = int(self.zoom_pos[1] - self.state_unit_h * self.zoom_range)
            bot_y = int(self.zoom_pos[1] + self.state_unit_h * self.zoom_range)

            temp = self.zoom_backup[top_y:bot_y, lef_x:rig_x]

            scale_w = (rig_x - lef_x) * self.zoom_scale
            scale_h = (bot_y - top_y) * self.zoom_scale
            dim = (int(scale_w), int(scale_h))

            if scale_w > 0 and scale_h > 0 and temp.shape[0] > 0 and temp.shape[1] > 0:
                temp_scale = cv.resize(temp, dim, interpolation=cv.INTER_AREA)

                t_x1, t_x2, t_y1, t_y2 = 0, int(scale_w), 0, int(scale_h)

                lef_x_new = int(self.zoom_pos[0] - scale_w / 2.0)
                rig_x_new = int(lef_x_new + scale_w)
                top_y_new = int(self.zoom_pos[1] - scale_h / 2.0)
                bot_y_new = int(top_y_new + scale_h)


                # boundary processing
                if lef_x_new <= self.state_plot_tl[0]:
                    t_x1 = int(self.state_plot_tl[0] - lef_x_new)
                    lef_x_new = int(self.state_plot_tl[0])
                    rig_x_new = int((t_x2 - t_x1) + lef_x_new)

                if rig_x_new >= self.state_plot_br[0]:
                    t_x2 = int(scale_w - (rig_x_new - self.state_plot_br[0]))
                    rig_x_new = int(self.state_plot_br[0])
                    lef_x_new = int(rig_x_new - (t_x2 - t_x1))

                if top_y_new <= self.state_plot_tl[1]:
                    t_y1 = int(self.state_plot_tl[1] - top_y_new)
                    top_y_new = int(self.state_plot_tl[1])
                    bot_y_new = int((t_y2 - t_y1) + top_y_new)

                if bot_y_new >= self.state_plot_br[1]:
                    t_y2 = int(scale_h - (bot_y_new - self.state_plot_br[1]))
                    bot_y_new = int(self.state_plot_br[1])
                    top_y_new = int(bot_y_new - (t_y2 - t_y1))


                self.img[top_y_new:bot_y_new, lef_x_new:rig_x_new] = temp_scale[t_y1:t_y2, t_x1:t_x2]

            # self.zoom_effect = False

        return


    # draw the crawler on the canvas
    def drawCrawler(self):
        self.crawler.draw(self.img)

    # draw the canvas
    def drawCanvas(self):
        self.img[:] = (255, 255, 255)  # fill the canvas to white
        self.img[round(self.canvas_h / 3):round(self.canvas_h - 1), 0:self.canvas_w] = (200, 200, 200)

        if self.show_analysis:
            # put the label "draw effect"
            cv.putText(self.img, 'Zoom effects:', (int(self.canvas_w * 0.03), int(self.canvas_h * 0.8)), self.font, 1.2, (0, 0, 0), 2, cv.LINE_AA)

        # sliding check
        if (abs(float(self.crawler.location[0] + self.x_shift - self.canvas_w)) < self.canvas_w * 0.1) and (not self.sliding_mode): # Left sliding
            self.sliding_mode = True
            self.slide_speed *= -1.0
            return
        elif (self.crawler.location[0] + self.x_shift <= self.canvas_w * 0.1) and (not self.sliding_mode):
            self.sliding_mode = True
        elif self.sliding_mode:
            if self.slide_counter < self.slide_size:
                self.x_shift += self.slide_speed
                self.slide_counter += 1

            else:
                self.slide_counter = 0

                # If slide towards left
                if self.slide_speed < 0:
                    self.slide_speed *= -1.0
                self.sliding_mode = False


        # draw coordinates
        if self.min_pos + self.x_shift < 0:
            self.min_idx += 1
            self.max_idx += 1
            self.min_pos += self.unit
            self.max_pos += self.unit

        elif self.max_pos + self.x_shift >= self.canvas_w:
            self.max_idx -= 1
            self.min_idx -= 1
            self.min_pos -= self.unit
            self.max_pos -= self.unit


        cur_min_pos = self.min_pos + self.x_shift
        for i in range(10):
            pos = (round(i * self.unit + cur_min_pos), round(self.ground_y + 40))
            cv.putText(self.img, str(i + self.min_idx), pos, self.font, 0.8, (0, 0, 0), 2, cv.LINE_AA)


        # Only redraw canvas one time for show-panel checkbox
        self.show_refresh = False

    def drawButtons(self):
        self.play_btn.draw(self.img)
        self.learning_btn.draw(self.img)
        self.reset_btn.draw(self.img)

        # Draw learning methods
        for i in range(len(self.option_learning_btns)):
            self.option_learning_btns[i].draw(self.img)

        if self.show_analysis:
            # Draw Zoom-range buttons
            for i in range(len(self.option_zoom_ranges)):
                self.option_zoom_ranges[i].draw(self.img)

            # Draw Zoom-scale Buttons
            for i in range(len(self.option_zoom_scale)):
                self.option_zoom_scale[i].draw(self.img)


        # Draw the 'show' option
        self.show_analysis_btn.draw(self.img)

    def onMouse(self, event, x, y, flags, param):
        x = int(x/self.scale)
        y = int(y/self.scale)

        if self.show_analysis:
            # Q-Panel
            if x >= self.q_plot_tl[0] and x <= self.q_plot_br[0] and y >= self.q_plot_tl[1] and y <= self.q_plot_br[1]:
                self.mouse_over_Q = True
                self.zoom_effect = False
            else:
                self.mouse_over_Q = False

            if event == cv.EVENT_LBUTTONDOWN and x >= self.q_plot_tl[0] and x <= self.q_plot_br[0] and y >= self.q_plot_tl[1] and y <= self.q_plot_br[1]:
                self.dragging_Q = True
                self.x_from_tl_q = x - self.q_plot_tl[0]
                self.x_from_br_q = self.q_plot_br[0] - x
                self.y_from_tl_q = y - self.q_plot_tl[1]
                self.y_from_br_q = self.q_plot_br[1] - y
            elif self.dragging_Q == True and event == cv.EVENT_LBUTTONUP:
                self.dragging_Q = False

            # Dragging the Q- panel
            if self.dragging_Q == True:
                if  int(x - self.x_from_tl_q) >= 0 and x + self.x_from_br_q < self.canvas_w and y - self.y_from_tl_q >= 0 and y + self.y_from_br_q < self.canvas_h:
                    self.q_plot_tl = (x - self.x_from_tl_q, y - self.y_from_tl_q)
                    self.q_plot_br = (x + self.x_from_br_q, y + self.y_from_br_q)


            # Detect Scaleing state view
            # scale_tl
            if not self.mouse_over_Q and ((abs(x - self.state_plot_tl[0]) < 9 and abs(y - self.state_plot_tl[1]) < 9 and self.dragging_state == False) or self.scale_tl == True):
                    cv.circle(self.img, self.state_plot_tl, 3, (0, 255, 255), 3)
            elif self.dragging_state == False and self.scale_tl == False:
                    cv.circle(self.img, self.state_plot_tl, 3, (0, 0, 255), 3)

            if not self.mouse_over_Q and event == cv.EVENT_LBUTTONDOWN and abs(x - self.state_plot_tl[0]) < 9 and abs(y - self.state_plot_tl[1]) < 9:
                self.scale_tl = True
            elif self.scale_tl and event == cv.EVENT_LBUTTONUP:
                self.scale_tl = False
                self.redraw_state = False
            if self.scale_tl:  # dragging top-left corner
                ratio = (self.state_plot_br[0] - self.state_plot_tl[0]) / (self.state_plot_br[1] - self.state_plot_tl[1])
                if (self.state_plot_br[0] - x) > ratio * (self.state_plot_br[1] - y): # x moves faster
                    y_new = self.state_plot_br[1] - (self.state_plot_br[0] - x) / ratio
                    if x >= 0 and int(y_new) >= 0:
                        self.state_plot_tl = (x, int(y_new))
                else: # y moves faster
                    x_new = self.state_plot_br[0] - (self.state_plot_br[1] - y) * ratio
                    if int(x_new) >=0 and y >=0:
                        self.state_plot_tl = (int(x_new), y)

                # Update the scene
                self.redraw_state = True
                self.state_img = np.zeros((self.state_plot_br[1] - self.state_plot_tl[1], self.state_plot_br[0] - self.state_plot_tl[0], 3), dtype=np.uint8)
                self.state_unit_w = (self.state_plot_br[0] - self.state_plot_tl[0]) / self.crawler.rl.cols
                self.state_unit_h = (self.state_plot_br[1] - self.state_plot_tl[1]) / self.crawler.rl.rows
                self.angle_1_label_pos = (int(self.state_plot_tl[0] - self.canvas_w * 0.03), int(self.state_plot_br[1] - self.canvas_h * 0.08)) # top left corner on canvas
                self.angle_2_label_pos = (int(self.state_plot_br[0] - 0.06 * self.canvas_w), int(self.state_plot_tl[1] - self.canvas_h * 0.01)) # top left corner on canvas




            # Detect dragging State Views
            if not self.mouse_over_Q and event == cv.EVENT_LBUTTONDOWN and x >= self.state_plot_tl[0] + 8 and x <= self.state_plot_br[0] - 8 and y >= self.state_plot_tl[1] + 8 and y <= self.state_plot_br[1] - 8:
                self.dragging_state = True
                self.x_from_tl = x - self.state_plot_tl[0]
                self.x_from_br = self.state_plot_br[0] - x
                self.y_from_tl = y - self.state_plot_tl[1]
                self.y_from_br = self.state_plot_br[1] - y
            elif not self.mouse_over_Q and self.dragging_state == True and event == cv.EVENT_LBUTTONUP:
                self.dragging_state = False

            # Dragging the state panel
            if self.dragging_state == True:
                if  int(x - self.x_from_tl) >= 0 and x + self.x_from_br < self.canvas_w and y - self.y_from_tl >= 0 and y + self.y_from_br < self.canvas_h:
                    self.state_plot_tl = (x - self.x_from_tl, y - self.y_from_tl)
                    self.state_plot_br = (x + self.x_from_br, y + self.y_from_br)
                    self.angle_1_label_pos = (int(self.state_plot_tl[0] - self.canvas_w * 0.03), int(self.state_plot_br[1] - self.canvas_h * 0.08))  # top left corner on canvas
                    self.angle_2_label_pos = (int(self.state_plot_br[0] - 0.06 * self.canvas_w), int(self.state_plot_tl[1] - self.canvas_h * 0.01))  # top left corner on canvas


            # Detect Scaleing state view
            # scale_tl
            if not self.mouse_over_Q and (abs(x - self.state_plot_tl[0]) < 9 and abs(y - self.state_plot_tl[1]) < 9 and self.dragging_state == False) or self.scale_tl == True:
                cv.circle(self.img, self.state_plot_tl, 3, (0, 255, 255), 3)
            elif not self.mouse_over_Q and self.dragging_state == False and self.scale_tl == False:
                cv.circle(self.img, self.state_plot_tl, 3, (0, 0, 255), 3)

            if not self.mouse_over_Q and event == cv.EVENT_LBUTTONDOWN and abs(x - self.state_plot_tl[0]) < 9 and abs(y - self.state_plot_tl[1]) < 9:
                self.scale_tl = True
            elif self.scale_tl and event == cv.EVENT_LBUTTONUP:
                self.scale_tl = False
                self.redraw_state = False
            if self.scale_tl:  # dragging top-left corner
                ratio = (self.state_plot_br[0] - self.state_plot_tl[0]) / (self.state_plot_br[1] - self.state_plot_tl[1])
                if (self.state_plot_br[0] - x) > ratio * (self.state_plot_br[1] - y): # x moves faster
                    y_new = self.state_plot_br[1] - (self.state_plot_br[0] - x) / ratio
                    if x >= 0 and int(y_new) >= 0:
                        self.state_plot_tl = (x, int(y_new))
                else: # y moves faster
                    x_new = self.state_plot_br[0] - (self.state_plot_br[1] - y) * ratio
                    if int(x_new) >=0 and y >=0:
                        self.state_plot_tl = (int(x_new), y)

                # Update the scene
                self.redraw_state = True
                self.state_img = np.zeros((self.state_plot_br[1] - self.state_plot_tl[1], self.state_plot_br[0] - self.state_plot_tl[0], 3), dtype=np.uint8)
                self.state_unit_w = (self.state_plot_br[0] - self.state_plot_tl[0]) / self.crawler.rl.cols
                self.state_unit_h = (self.state_plot_br[1] - self.state_plot_tl[1]) / self.crawler.rl.rows
                self.angle_1_label_pos = (int(self.state_plot_tl[0] - self.canvas_w * 0.03), int(self.state_plot_br[1] - self.canvas_h * 0.08)) # top left corner on canvas
                self.angle_2_label_pos = (int(self.state_plot_br[0] - 0.06 * self.canvas_w), int(self.state_plot_tl[1] - self.canvas_h * 0.01)) # top left corner on canvas

            # scale_br
            if (abs(x - self.state_plot_br[0]) < 9 and abs(y - self.state_plot_br[1]) < 9 and self.dragging_state == False) or self.scale_br == True:
                cv.circle(self.img, self.state_plot_br, 3, (0, 255, 255), 3)
            elif not self.mouse_over_Q and self.dragging_state == False and self.scale_br == False:
                cv.circle(self.img, self.state_plot_br, 3, (0, 0, 255), 3)

            if not self.mouse_over_Q and event == cv.EVENT_LBUTTONDOWN and abs(x - self.state_plot_br[0]) < 9 and abs(y - self.state_plot_br[1]) < 9:
                self.scale_br = True
            elif self.scale_br and event == cv.EVENT_LBUTTONUP:
                self.scale_br = False
                self.redraw_state = False
            if self.scale_br:  # dragging top-left corner
                ratio = (self.state_plot_br[0] - self.state_plot_tl[0]) / (self.state_plot_br[1] - self.state_plot_tl[1])
                if (x - self.state_plot_tl[0]) > ratio * (y - self.state_plot_tl[1]):  # x moves faster
                    y_new = self.state_plot_tl[1] + (x - self.state_plot_tl[0]) / ratio
                    if x < self.canvas_w and int(y_new) < self.canvas_h:
                        self.state_plot_br = (x, int(y_new))
                else:  # y moves faster
                    x_new = self.state_plot_tl[0] + (y - self.state_plot_tl[1]) * ratio
                    if int(x_new) < self.canvas_w and y < self.canvas_h:
                        self.state_plot_br = (int(x_new), y)

                # Update the scene
                self.redraw_state = True
                self.state_img = np.zeros(
                    (self.state_plot_br[1] - self.state_plot_tl[1], self.state_plot_br[0] - self.state_plot_tl[0], 3),
                    dtype=np.uint8)
                self.state_unit_w = (self.state_plot_br[0] - self.state_plot_tl[0]) / self.crawler.rl.cols
                self.state_unit_h = (self.state_plot_br[1] - self.state_plot_tl[1]) / self.crawler.rl.rows
                self.angle_1_label_pos = (int(self.state_plot_tl[0] - self.canvas_w * 0.03),
                                          int(self.state_plot_br[1] - self.canvas_h * 0.08))  # top left corner on canvas
                self.angle_2_label_pos = (int(self.state_plot_br[0] - 0.06 * self.canvas_w),
                                          int(self.state_plot_tl[1] - self.canvas_h * 0.01))  # top left corner on canvas


            #zoom
            if not self.mouse_over_Q and self.play_mode == False and x >= self.state_plot_tl[0] + 8 and x <= self.state_plot_br[0] - 8 and y >= self.state_plot_tl[1] + 8 and y <= self.state_plot_br[1] - 8:
                self.zoom_effect = True
                self.zoom_pos = (x, y)
                self.zoom_r = int((y - self.state_plot_tl[1]) / self.state_unit_h)
                self.zoom_c = int((x - self.state_plot_tl[0]) / self.state_unit_w)

                if self.show_analysis:
                    self.drawQpanel()
                # print('angle1: ' + str(self.angle1) + ', angle2: ' + str(self.angle2))

                # for i in range(3):
                #     print(f"{self.crawler.rl.Qvalue[r][9 * c + 3 * i + 0]:.1f}" + ', ' + f"{self.crawler.rl.Qvalue[r][9 * c + 3 * i + 1]:.1f}"  + ', ' + f"{self.crawler.rl.Qvalue[r][9 * c + 3 * i + 2]:.1f}"  )

            if x < self.state_plot_tl[0] + 8 or x > self.state_plot_br[0] - 8 or y < self.state_plot_tl[1] + 8 or y > self.state_plot_br[1] - 8:
                self.img = self.zoom_backup
                self.drawCanvas()
                self.drawCrawler()
                self.drawButtons()

                if self.show_analysis:
                    self.drawStates()
                    self.drawQpanel()
                self.zoom_effect = False

            # Zoom ranges radio buttons
            for i in range(len(self.option_zoom_ranges)):
                option_select = False
                if event == cv.EVENT_LBUTTONDOWN and not self.dragging_state and not self.mouse_over_Q and x >= \
                        self.option_zoom_ranges[i].top_left[0] and x <= self.option_zoom_ranges[i].bot_right[
                    0] and y >= self.option_zoom_ranges[i].top_left[1] and y <= \
                        self.option_zoom_ranges[i].bot_right[1]:
                    if self.option_zoom_ranges[i].selected:
                        break
                    else:
                        self.option_zoom_ranges[i].selected = True
                        if i == 0:
                            self.zoom_range = 1
                        elif i == 1:
                            self.zoom_range = 1.5
                        else:
                            self.zoom_range = 2
                        for j in range(len(self.option_zoom_ranges)):
                            if j != i:
                                self.option_zoom_ranges[j].selected = False

            # Zoom scale radio buttons
            for i in range(len(self.option_zoom_scale)):
                option_select = False
                if event == cv.EVENT_LBUTTONDOWN and not self.dragging_state and not self.mouse_over_Q and x >= \
                        self.option_zoom_scale[i].top_left[0] and x <= self.option_zoom_scale[i].bot_right[
                    0] and y >= self.option_zoom_scale[i].top_left[1] and y <= \
                        self.option_zoom_scale[i].bot_right[1]:
                    if self.option_zoom_scale[i].selected:
                        break
                    else:
                        self.option_zoom_scale[i].selected = True
                        if i == 0:
                            self.zoom_scale = 1
                        elif i == 1:
                            self.zoom_scale = 2
                        else:
                            self.zoom_scale = 3
                        for j in range(len(self.option_zoom_scale)):
                            if j != i:
                                self.option_zoom_scale[j].selected = False


        # play button
        if not self.zoom_effect and not self.mouse_over_Q and self.play_btn.over == False and x >= self.play_btn.top_left[0] and x <= self.play_btn.bot_right[0] and y >= self.play_btn.top_left[1] and y <= self.play_btn.bot_right[1]:
            self.play_btn.over = True
            self.draw_btns = True


        if self.play_btn.over and not(x >= self.play_btn.top_left[0] and x <= self.play_btn.bot_right[0] and y >= self.play_btn.top_left[1] and y <= self.play_btn.bot_right[1]):
            self.play_btn.over = False
            self.draw_btns = True

        # learning button skip 50,000
        if not self.zoom_effect and not self.mouse_over_Q and self.learning_btn.over == False and x >= self.learning_btn.top_left[0] and x <= self.learning_btn.bot_right[0] and y >= self.learning_btn.top_left[1] and y <= self.learning_btn.bot_right[1]:
            self.learning_btn.over = True
            self.draw_btns = True

        if self.learning_btn.over and not (x >= self.learning_btn.top_left[0] and x <= self.learning_btn.bot_right[0] and y >= self.learning_btn.top_left[1] and y <= self.learning_btn.bot_right[1]):
            self.learning_btn.over = False
            self.draw_btns = True


        # Reset button
        if not self.zoom_effect and not self.mouse_over_Q and self.reset_btn.over == False and x >= self.reset_btn.top_left[0] and x <= self.reset_btn.bot_right[0] and y >= self.reset_btn.top_left[1] and y <= self.reset_btn.bot_right[1]:
            self.reset_btn.over = True
            self.draw_btns = True


        if self.reset_btn.over and not(x >= self.reset_btn.top_left[0] and x <= self.reset_btn.bot_right[0] and y >= self.reset_btn.top_left[1] and y <= self.reset_btn.bot_right[1]):
            self.reset_btn.over = False
            self.draw_btns = True

        # play button click
        if event == cv.EVENT_LBUTTONDOWN and self.play_btn.over:
            if self.play_btn.clicked:
                self.play_btn.clicked = False
                self.play_mode = False
            else:
                self.play_btn.clicked = True
                self.play_mode = True
            self.draw_btns = True

        # learning button skip 50,000 click
        if event == cv.EVENT_LBUTTONDOWN and self.learning_btn.over:
            self.learning_btn.clicked = True
            self.draw_btns = True

        # Reset button
        if event == cv.EVENT_LBUTTONDOWN and self.reset_btn.over:
            self.play_mode = False
            self.reset_btn.clicked = True
            self.play_btn.clicked = False
            self.crawler.angle1 = 0
            self.crawler.angle2 = 0
            self.crawler.rl.reset()
            self.draw_btns = True
            self.redraw_state = True


        # Learning Option radio buttons
        for i in range(len(self.option_learning_btns)):
            option_select = False
            if event == cv.EVENT_LBUTTONDOWN and not self.dragging_state and not self.mouse_over_Q and x >= self.option_learning_btns[i].top_left[0] and x <= self.option_learning_btns[i].bot_right[0] and y >= self.option_learning_btns[i].top_left[1] and y <= self.option_learning_btns[i].bot_right[1]:
                if self.option_learning_btns[i].selected:
                    break
                else:
                    self.option_learning_btns[i].selected = True
                    for j in range(len(self.option_learning_btns)):
                        if j != i:
                            self.option_learning_btns[j].selected = False

                    self.play_mode = False
                    self.play_btn.clicked = False
                    self.crawler.rl.reset()
                    self.draw_btns = True
                    self.redraw_state = True

                    if i == 0:
                        self.play_option = 0
                        cv.setTrackbarPos('Iterations (k):', 'window', 50)
                        cv.setTrackbarPos('e-greedy %', 'window', 20)
                        cv.setTrackbarPos('Discount %', 'window', 95)
                        self.crawler.rl.steps = 50 * 10
                        self.learning_btn.text = 'Skip '+ str(self.crawler.rl.steps) +' steps'
                    elif i == 1:
                        self.play_option = 1
                        cv.setTrackbarPos('Iterations (k):', 'window', 100)
                        cv.setTrackbarPos('Learning rate %', 'window', 60)
                        cv.setTrackbarPos('e-greedy %', 'window', 20)
                        cv.setTrackbarPos('Discount %', 'window', 95)
                        self.crawler.rl.steps = 100 * 1000
                        self.learning_btn.text = 'Skip ' + str(self.crawler.rl.steps) + ' steps'
                    elif i == 2:
                        self.play_option = 2
                        cv.setTrackbarPos('Iterations (k):', 'window', 50)
                        cv.setTrackbarPos('Learning rate %', 'window', 20)
                        cv.setTrackbarPos('e-greedy %', 'window', 20)
                        cv.setTrackbarPos('Discount %', 'window', 95)
                        self.crawler.rl.steps = 50 * 1000
                        self.learning_btn.text = 'Skip '+ str(self.crawler.rl.steps) +' steps'

                    self.draw_btns = True
                    break



        if event == cv.EVENT_LBUTTONDOWN and not self.scale_br and not self.scale_tl and not self.dragging_state and not self.mouse_over_Q and x >= self.show_analysis_btn.check_box_p1[0] -3 and x <=  self.show_analysis_btn.check_box_p2[0]+3 and y >= self.show_analysis_btn.check_box_p1[1]-3 and y <= self.show_analysis_btn.check_box_p2[1]+3:
            if self.show_analysis_btn.selected:
                self.show_analysis_btn.selected = False
                self.show_analysis = False

            else:
                self.show_analysis_btn.selected = True
                self.show_analysis = True

            self.show_refresh = True
        return




    def setAlpha(self, val):
        # condition to change color if trackbar value is greater than 127
        self.crawler.rl.alpha = float(val/100.0)

    def setGamma(self, val):
        self.crawler.rl.gamma = float(val/100)


    def setEpsilon(self, val):
        self.crawler.rl.epsilon = float(val/100)


    def setSteps(self, val):
        if self.play_option == 0:
            self.crawler.rl.steps = int(val) * 10
        elif self.play_option == 1:
            self.crawler.rl.steps = int(val) * 1000
        elif self.play_option == 2:
            self.crawler.rl.steps = int(val) * 1000

        self.learning_btn.text = 'Skip '+ str(self.crawler.rl.steps) +' steps'
        self.draw_btns = True

    def run(self):
        self.drawCanvas()
        self.drawCrawler()
        self.drawButtons()

        if self.show_analysis:
            self.drawStates()
            self.drawQpanel()

        cv.namedWindow('window')
        cv.createTrackbar('Iterations (k):', 'window', 50, 100, self.setSteps)
        cv.createTrackbar('Learning rate %', 'window', 20, 100, self.setAlpha)
        cv.createTrackbar('Discount %', 'window', 95, 100, self.setGamma)
        cv.createTrackbar('e-greedy %', 'window', 20, 100, self.setEpsilon)
        cv.setMouseCallback('window', self.onMouse)


        while (1):

            # Redraw the button if mouse moves over or click
            if self.draw_btns:
                self.drawButtons()
                self.draw_btns = False

            if self.dragging_state or self.scale_tl:
                self.drawStates()


            # Do the Q-learning
            if self.learning_btn.clicked and self.btn_counter > 1:
                # learning process
                self.crawler.rl.onLearningProxy(option=self.play_option)
                self.learning_btn.clicked = False
                self.draw_btns = True
                self.btn_counter = 0  # Used to refresh the screen before learning
                self.redraw_state = True
            elif self.learning_btn.clicked:
                self.btn_counter += 1

            # Do the Reset-Button
            if self.reset_btn.clicked and self.btn_counter > 1:
                self.draw_btns = True
                self.reset_btn.clicked = False
                self.btn_counter = 0  # Used to refresh the screen before learning
            elif self.reset_btn.clicked:
                self.btn_counter += 1

            # Re-draw the screen if state change
            if (self.crawler.angle1 != self.crawler.angle1_last) or (
                    self.crawler.angle2 != self.crawler.angle2_last) or self.sliding_mode or self.dragging_state or self.scale_tl or self.redraw_state or self.zoom_effect or self.dragging_Q or self.show_refresh:
                # reset the crawler position first
                self.crawler.posConfig(self.x_shift, self.sliding_mode)

                # draw the canvas according to the crawler location
                self.drawCanvas()

                # draw the crawler
                self.drawCrawler()

                # draw the buttons
                self.drawButtons()

                if self.show_analysis:
                    # draw the states
                    self.drawStates()

                    # draw the Q-panel
                    self.drawQpanel()


            # Each iteration run angle update automatically
            if self.play_mode:
                self.crawler.angle1, self.crawler.angle2 = self.crawler.rl.onPlay(self.crawler.angle1, self.crawler.angle2)


            c = cv.waitKey(1)
            if c == 27:
                break
            elif c == 119 or c == 87:  # W
                if self.crawler.angle1 >= (self.crawler.rl.angle1_range[0] + self.crawler.motion_unit):
                    self.crawler.angle1_last = self.crawler.angle1
                    self.crawler.angle1 -= self.crawler.motion_unit
                    # self.crawler.angle2_last = self.crawler.angle2
                    # self.crawler.angle2 -= crawler.motion_unit
            elif c == 83 or c == 115:  # S
                if self.crawler.angle1 <= (self.crawler.rl.angle1_range[1] - self.crawler.motion_unit):
                    self.crawler.angle1_last = self.crawler.angle1
                    self.crawler.angle1 += self.crawler.motion_unit
                    # self.crawler.angle2_last = self.crawler.angle2
                    # self.crawler.angle2+=crawler.motion_unit
            elif c == 97 or c == 65:  # A
                if self.crawler.angle2 <= (self.crawler.rl.angle2_range[1] - self.crawler.motion_unit):
                    self.crawler.angle2_last = self.crawler.angle2
                    self.crawler.angle2 += self.crawler.motion_unit
            elif c == 100 or c == 68:  # D
                if self.crawler.angle2 >= (self.crawler.rl.angle2_range[0] + self.crawler.motion_unit):
                    self.crawler.angle2_last = self.crawler.angle2
                    self.crawler.angle2 -= self.crawler.motion_unit


            elif c == 32: # space
                if self.play_mode:
                    self.play_mode = False
                    self.play_btn.clicked = False
                else:
                    self.play_mode = True
                    self.play_btn.clicked = True

            elif c == 113 or c == 81: # q
                if self.drawQ:
                    self.drawQ = False
                else:
                    self.drawQ = True

                self.redraw_state = True





            w = round(self.img.shape[1] * self.scale)
            h = round(self.img.shape[0] * self.scale)
            dim = (w, h)
            img_show = cv.resize(self.img, dim, interpolation=cv.INTER_AREA)
            cv.imshow("window", img_show)
            # cv.imshow('window 2', self.angle_2_img)


        # It is for removing/deleting created GUI window from screen
        # and memory
        cv.destroyAllWindows()



def main():

    # GUI part
    screen_scale = 0.5
    width = 2000
    height = 1500
    ground_y = height / 3
    crawler_body_w = width / 10
    crawler_body_h = width / 20
    crawler_location = (int(width * 0.15), int(height / 3 - crawler_body_h / 2))
    crawler_arm1 = crawler_body_w / 2
    crawler_arm2 = crawler_body_w / 2
    crawler_angle_change_unit = 5  # the degrees of change every time
    contact_precision = 0.1

    # create a learner
    rl = RL()

    # Initialize the crawler
    crawler = Crawler(location=crawler_location, height=crawler_body_h, width=crawler_body_w, arm1=crawler_arm1,
                      arm2=crawler_arm2, ground_y=ground_y, motion_unit=crawler_angle_change_unit,
                      precision=contact_precision, learner=rl)


    screen = Environment(crawler=crawler, width=width, height=height, scale=screen_scale)


    # configure the learner by providing crawler's info
    rl.setBot(crawler=crawler)

    # starts the GUI loop
    screen.run()


if __name__ == "__main__":
    main()