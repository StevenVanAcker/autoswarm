#!/usr/bin/env python3

from autoswarm import AutoSwarmMaster
import logging

if __name__ == "__main__":
    master = AutoSwarmMaster()
    master.logger.setLevel(logging.DEBUG)
    master.run()





