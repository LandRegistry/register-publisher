#!/bin/python
import logging

NAME = __name__ + '.audit'
LEVEL = logging.DEBUG

class AuditLogger(logging.getLoggerClass()):
    """ Custom logging class, to ensure that audit log calls always succeed. """

    def __init__(self, name=NAME):
        """ Specify lowest level possible (above NOTSET), to avoid delegation to parent. """
        super().__init__(name, level=LEVEL)

        # Prevent messages from being passed upwards to ancestors.
        self.propagate = False

    def _checkLevel(level):
        """ Make sure that Handlers, Filterers etc. cannot change the level either. """

        return LEVEL

    def setLevel(self, level):
        raise NotImplementedError("All logging levels need to be effective for audit purposes. ")

    def disable(self, level):
        raise NotImplementedError("All logging levels need to be effective for audit purposes. ")


logging.setLoggerClass(AuditLogger)

audit = logging.getLogger(NAME)
