#!/bin/bash

# git repo directory
REPODIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$REPODIR"

mode=$1

while true;
do
	# until forever: update and start slave
	git pull
	case $mode in
	    slave)
		./autoswarm.py
		;;
	    master)
		./autoswarm-master.py
		;;
	esac
	sleep 1 # avoid busy-loop
done
