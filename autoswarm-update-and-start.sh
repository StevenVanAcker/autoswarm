#!/bin/bash

# git repo directory
REPODIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$REPODIR"

mode=$1
addr=$2

while true;
do
	# until forever: update and start slave
	git pull
	case $mode in
	    slave)
		./autoswarm.py
		;;
	    master)
		./autoswarm-master.py $addr
		;;
	esac
	sleep 1 # avoid busy-loop
done
