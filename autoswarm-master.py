#!/usr/bin/env python3

from autoswarm import AutoSwarmMaster
import logging, sys

if __name__ == "__main__":
    master = AutoSwarmMaster()
    master.logger.setLevel(logging.DEBUG)
    if len(sys.argv) > 1:
        master.setAddress(sys.argv[1])
    master.run()





