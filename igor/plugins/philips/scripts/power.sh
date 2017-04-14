#!/bin/bash
dirPhilips=~jack/src/dis/jack/bin
philipsPowerCmd="ssh jack@mediacentre.local python bin/tvcmd.py "
case x$igor_power in
xon|xtrue)
	$philipsPowerCmd 32
	echo Philips powered on
	;;
xoff|xfalse|x)
	$philipsPowerCmd 12
	echo Philips powered off
	;;
*)
	echo Unknown Philips power state $igor_power
esac
