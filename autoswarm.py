#!/usr/bin/env python3

import time
import docker
import boto3, botocore
import pprint
import threading
import json
import copy
import subprocess
import collections
import logging
import random, string

class AutoSwarmCommon():
        SQS_QUEUE_MASTER = "AutoSwarmMaster"

        def __init__(self): #{{{
            self.logger = logging.getLogger(self.__class__.__name__)
            self.logger.setLevel(logging.WARNING)
            ch = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)
#}}}
        def get_maybe_create_queue(self, queuename): #{{{
            sqs = boto3.resource('sqs') 
            inq = None
            try:
                inq = sqs.get_queue_by_name(QueueName=queuename)
                return inq
            except Exception as e:
                inq = sqs.create_queue(QueueName=queuename)
            return inq
#}}}
        def send_message_to_queue(self, queuename, msg): #{{{
            q = self.get_maybe_create_queue(queuename)
            if q != None:
                q.send_message(MessageBody=json.dumps(msg))
                return True
            return False
#}}}
        def maybe_delete_queue(self, queuename): #{{{
            sqs = boto3.resource('sqs') 
            try:
                inq = sqs.get_queue_by_name(QueueName=queuename)
                inq.delete()
            except Exception as e:
                self.logger.error("maybe_delete_queue(): {}".format(e))
                pass
#}}}

class AutoSwarmSlave(AutoSwarmCommon):
        MSGMAXWAIT = 15
        LOOPTIME = 30

        def __init__(self): #{{{
            super().__init__()
            self.queue = None
#}}}
        def processMessageFromMaster(self): # FIXME {{{
            try:
                sqs = boto3.resource('sqs') 
                inq = self.get_maybe_create_queue(self.queue)

                for msg in inq.receive_messages(WaitTimeSeconds = self.MSGMAXWAIT, MaxNumberOfMessages=1, MessageAttributeNames=['All']):
                    self.logger.debug("Message received: {}".format(msg.body))
                    msgdata = json.loads(msg.body)
                    msg.delete()

                    if msgdata["cmd"] == "join":
                        if self.joinSwarm(msgdata["master"], msgdata["jointoken"]):
                            self.logger.debug("Successfully joined swarm")
                        else:
                            self.logger.debug("Failed to join swarm")

            except botocore.exceptions.NoRegionError as e:
                self.logger.error("processMessageFromMaster() received NoRegionError from boto3: {}".format(e))
                time.sleep(1)
            except Exception as e:
                self.logger.error("processMessageFromMaster() threw an exception: {}".format(e))
#}}}
        def joinSwarm(self, master, token): #{{{
            try:
                d = docker.from_env()
                return d.swarm.join(
                        remote_addrs=[master], 
                        listen_addr="0.0.0.0",
                        join_token=token
                        )
            except Exception as e:
                self.logger.error("joinSwarm() threw exception: {}".format(e))
            return False
#}}}
        def joinedSwarm(self): #{{{
            try:
                d = docker.from_env()
                return "active" == d.info()["Swarm"]["LocalNodeState"]
            except Exception as e:
                self.logger.error("joinedSwarm() threw exception: {}".format(e))
                
            return False 
#}}}
        def run(self): #{{{
            while True:
                if not self.joinedSwarm():
                    self.queue = "AutoSwarmSlave-" + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
                    print("queue = {}".format(self.queue))
                    self.get_maybe_create_queue(self.queue)
                    self.send_message_to_queue(self.SQS_QUEUE_MASTER, {
                            "cmd": "join",
                            "timestamp": time.time(),
                            "queue": self.queue
                    })
                    self.processMessageFromMaster()
                    self.maybe_delete_queue(self.queue)
                    self.queue = None
                time.sleep(self.LOOPTIME)
#}}}


# loop and read all messages, then send same recipe to all hosts
class AutoSwarmMaster(AutoSwarmCommon):
        MSGMAXWAIT = 15
        MSGMAXAGE = 10

        def initSwarm(self): #{{{
            try:
                d = docker.from_env()
                return d.swarm.init()
            except Exception as e:
                self.logger.debug("Swarm init {}".format(e))
            return None
#}}}
        def getJoinToken(self): #{{{
            try:
                d = docker.from_env()
                return d.swarm.attrs["JoinTokens"]["Worker"]
            except Exception as e:
                self.logger.debug("Could not get docker swarm join-token: {}".format(e))
            return None
#}}}
        def getMasterAddress(self): #{{{
            try:
                d = docker.from_env()
                return d.info()["Swarm"]["RemoteManagers"][0]["Addr"]
            except Exception as e:
                self.logger.debug("Could not get docker swarm master address: {}".format(e))
            return None
#}}}
        def processMessageFromSlaves(self): # {{{
            try:
                sqs = boto3.resource('sqs') 
                inq = self.get_maybe_create_queue(self.SQS_QUEUE_MASTER)

                for msg in inq.receive_messages(WaitTimeSeconds = self.MSGMAXWAIT, MaxNumberOfMessages=10, MessageAttributeNames=['All']):
                    self.logger.debug("Message received: {}".format(msg.body))
                    msgdata = json.loads(msg.body)
                    msg.delete()

                    if msgdata["timestamp"] > time.time() - self.MSGMAXAGE:
                        self.logger.debug("Processing: {}".format(msgdata))
                        jointoken = self.getJoinToken()
                        masteraddress = self.getMasterAddress()
                        if jointoken != None and masteraddress != None:
                            self.logger.debug("Sending back join-token and master address")
                            self.send_message_to_queue(msgdata["queue"], {
                                "cmd": "join",
                                "timestamp": time.time(),
                                "jointoken": jointoken,
                                "master": masteraddress
                            })
                        else:
                            self.logger.debug("Could not get information, ignoring slave for now")
                    else:
                        self.logger.debug("Discarding: {}".format(msgdata))
            except botocore.exceptions.NoRegionError as e:
                self.logger.error("processMessageFromSlaves() received NoRegionError from boto3: {}".format(e))
                time.sleep(1)
            except Exception as e:
                self.logger.error("processMessageFromSlaves() threw an exception: {}".format(e))
#}}}
        def run(self): #{{{
            self.initSwarm()
            while True:
                self.processMessageFromSlaves()
#}}}

if __name__ == "__main__":

    slave = AutoSwarmSlave()
    #slave.logger.setLevel(logging.INFO)
    slave.logger.setLevel(logging.DEBUG)
    slave.run()





