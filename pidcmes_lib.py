#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    class Pidcmes
    =============
    Measure an analog voltage on two digital pins.
    The measuring range starts just above the reference voltage and can go from TRIG_LEVEL+0.2 up to more than 15V.
    The lower the voltage measured, the longer the measurement takes. The precison is about +/- 0.2V

    Constants : PIN_CMD -> control pin
                PIN_MES -> measure pin
                TRIG_LEVEL -> comparator refenre voltage
                R1 -> resistor of RC circuit for time measurement
                C1 -> condensator of RC circuit for time measurement
                PULSE_WIDTH -> duration of the condensator discharge pulse
                T_TIMEOUT -> after this this the measure is stopedd because no tension on the measurement pins
                FILTER -> standard deviation accepted for good measurement

    Errors :  0 -> measurement is ok
              1 -> no tension on the measure pin
              2 -> n_mean < 2
              3 -> not enought measure for st_dev (standard deviation)
"""

import time
import RPi.GPIO as GPIO
import math


class Pidcmes:

    def __init__(self):
        # initialize program constants
        self.PIN_CMD = 8  # control pin
        self.PIN_MES = 10  # measure pin
        self.TRIG_LEVEL = 2.5  # comparator reference voltage
        self.R1 = 100e3  # resistor value 100 k
        self.C1 = 1e-6  # condensator value 1 uF
        self.PULSE_WIDTH = 10e-3  # pulse width to discharge the condensator and trig the measure
        self.T_TIMEOUT = 10 * self.R1 * self.C1  # if no interruption after 10 R1*C1 time -> no tension on the measure pin
        self.FILTER = 1.5  # +/- filter on n standard deviation to exclude bad measurement

        # initialisation GPIO
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        GPIO.setup(self.PIN_CMD, GPIO.OUT)  # initialize control pin                  
        GPIO.setup(self.PIN_MES, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # initialize measure pi (attention no pull-up or pull-down)
        GPIO.output(self.PIN_CMD, GPIO.LOW)

    def get_tension(self, n_mean):

        # verifiy the value of n_for_mean
        if n_for_mean < 2:  # n_for_mean must be greather than 1
            err = 2
            msg = "n_for_mean must be greather than 1"
            return 0, err, msg

        l_elapsed = []
        err = 0
        msg = "Measure ok"

        # read the tension
        for dummy in range(n_mean):

            # trig the measure
            GPIO.output(self.PIN_CMD, GPIO.HIGH)  # discharge condensator
            time.sleep(self.PULSE_WIDTH)
            GPIO.output(self.PIN_CMD, GPIO.LOW)  # start the measurement

            t_start_measure = time.time()  # start stopwatch
            # wait for GPIO.FALLING on pin 'PIN_MES'
            channel = GPIO.wait_for_edge(self.PIN_MES, GPIO.FALLING, timeout=int(self.T_TIMEOUT * 2000))
            # GPIO.FALLING occurs
            if channel is not None:  # measure is ok
                elapsed = (time.time() - t_start_measure)
                l_elapsed.append(elapsed)
            else:  # timeout has occcured
                err = 1
                msg = "timeout has occured"
                return 0, err, msg

        # Pidcmes.in_run = False
        # filter the data list on the standard deviation

        n = len(l_elapsed)  # number of measurements
        v_mean = sum(l_elapsed) / n  # mean value
        st_dev = math.sqrt(sum([(x - v_mean) ** 2 for x in l_elapsed]) / (n - 1))  # standard deviation
        if st_dev == 0:
            return v_mean, 0, msg

        # filter on max stdev = FILTER value
        l_elaps_f = [el for el in l_elapsed if abs((el - v_mean) / st_dev) <= self.FILTER]
        l_elaps_f_mean = sum(l_elaps_f) / len(l_elaps_f)  # mean of elaps filtered

        # calculate  the tension
        u_average = self.TRIG_LEVEL / (1 - math.exp(-l_elaps_f_mean / (self.R1 * self.C1)))
        return u_average, err, msg


if __name__ == '__main__':

    # verify tension and filtering
    pidcmes = Pidcmes()
    n_for_mean = 10  # the greater this value, the longer the measurement takes
    u, err_no, err_msg = pidcmes.get_tension(n_for_mean)
    if err_no == 0:  # the measurement is ok
        print(err_msg + " -> " + "la tension sur l'entrée de mesure est de: " + '{:.1f}'.format(u) + " [V]")
    elif err_no == 1:  # no tesnion on the measure entry
        print(err_msg + " -> " + "Pas de tension détectée sur l'entrée de mesure")
    elif err_no == 2:  # n_for_mean < 2
        print(err_msg + " -> " + "la valeur de n_for_mean doit etre >= 2")
    GPIO.cleanup()
