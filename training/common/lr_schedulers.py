import copy
import math
import logging


class TriangularSchedule():

    def __init__(self, min_lr, max_lr, cycle_length, inc_fraction=0.5):
        """
        min_lr: lower bound for learning rate (float)
        max_lr: upper bound for learning rate (float)
        cycle_length: iterations between start and finish (int)
        inc_fraction: fraction of iterations spent in increasing stage (float)
        """
        self.min_lr = min_lr
        self.max_lr = max_lr
        self.cycle_length = cycle_length
        self.inc_fraction = inc_fraction

    def __call__(self, iteration):
        if iteration <= self.cycle_length * self.inc_fraction:
            unit_cycle = iteration * 1 / (self.cycle_length * self.inc_fraction)
        elif iteration <= self.cycle_length:
            unit_cycle = (self.cycle_length - iteration) * 1 / (self.cycle_length * (1 - self.inc_fraction))
        else:
            unit_cycle = 0
        adjusted_cycle = (unit_cycle * (self.max_lr - self.min_lr)) + self.min_lr
        return adjusted_cycle


class CosineAnnealingSchedule():

    def __init__(self, min_lr, max_lr, cycle_length):
        """
        min_lr: lower bound for learning rate (float)
        max_lr: upper bound for learning rate (float)
        cycle_length: iterations between start and finish (int)
        """
        self.min_lr = min_lr
        self.max_lr = max_lr
        self.cycle_length = cycle_length

    def __call__(self, iteration):
        if iteration <= self.cycle_length:
            unit_cycle = (1 + math.cos(iteration * math.pi / self.cycle_length)) / 2
            adjusted_cycle = (unit_cycle * (self.max_lr - self.min_lr)) + self.min_lr
            return adjusted_cycle
        else:
            return self.min_lr


class LinearWarmUp():

    def __init__(self, schedule, start_lr, length):
        """
        schedule: a pre-initialized schedule (e.g. TriangularSchedule(min_lr=0.5, max_lr=2, cycle_length=500))
        start_lr: learning rate used at start of the warm-up (float)
        length: number of iterations used for the warm-up (int)
        """
        self.schedule = schedule
        self.start_lr = start_lr
        # calling mx.lr_scheduler.LRScheduler effects state, so calling a copy
        self.finish_lr = copy.copy(schedule)(0)
        self.length = length

    def __call__(self, iteration):
        if iteration <= self.length:
            return iteration * (self.finish_lr - self.start_lr) / (self.length) + self.start_lr
        else:
            return self.schedule(iteration - self.length)


class LinearCoolDown():

    def __init__(self, schedule, finish_lr, start_idx, length):
        """
        schedule: a pre-initialized schedule (e.g. TriangularSchedule(min_lr=0.5, max_lr=2, cycle_length=500))
        finish_lr: learning rate used at end of the cool-down (float)
        start_idx: iteration to start the cool-down (int)
        length: number of iterations used for the cool-down (int)
        """
        self.schedule = schedule
        # calling mx.lr_scheduler.LRScheduler effects state, so calling a copy
        self.start_lr = copy.copy(self.schedule)(start_idx)
        self.finish_lr = finish_lr
        self.start_idx = start_idx
        self.finish_idx = start_idx + length
        self.length = length

    def __call__(self, iteration):
        if iteration <= self.start_idx:
            return self.schedule(iteration)
        elif iteration <= self.finish_idx:
            return (iteration - self.start_idx) * (self.finish_lr - self.start_lr) / (self.length) + self.start_lr
        else:
            return self.finish_lr


class OneCycleSchedule():

    def __init__(self, start_lr, max_lr, cycle_length, cooldown_length=0, finish_lr=None):
        """
        start_lr: lower bound for learning rate in triangular cycle (float)
        max_lr: upper bound for learning rate in triangular cycle (float)
        cycle_length: iterations between start and finish of triangular cycle: 2x 'stepsize' (int)
        cooldown_length: number of iterations used for the cool-down (int)
        finish_lr: learning rate used at end of the cool-down (float)
        """
        if (cooldown_length > 0) and (finish_lr is None):
            raise ValueError("Must specify finish_lr when using cooldown_length > 0.")
        if (cooldown_length == 0) and (finish_lr is not None):
            raise ValueError("Must specify cooldown_length > 0 when using finish_lr.")

        logging.info('Setting up one-cycle schedule w/ start_lr=%e, max_lr=%e, cycle_length=%d, cooldown_length=%d, finish_lr=%e' % (start_lr, max_lr, cycle_length, cooldown_length, finish_lr))

        finish_lr = finish_lr if (cooldown_length > 0) else start_lr
        schedule = TriangularSchedule(min_lr=start_lr, max_lr=max_lr, cycle_length=cycle_length)
        self.schedule = LinearCoolDown(schedule, finish_lr=finish_lr, start_idx=cycle_length, length=cooldown_length)

    def __call__(self, iteration):
        lr = self.schedule(iteration)
        if iteration % 10000 == 0:
            logging.info("Update[%d]: Change learning rate to %0.5e", iteration, lr)
        return lr

