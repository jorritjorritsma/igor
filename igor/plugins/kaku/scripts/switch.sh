#!/bin/bash
dir=`dirname $0`
dirIgor=$dir/../../..
dirKAKU=$dirIgor/../helpers/kaku
commandPrefix=""
case x$igor_host in
x)
	;;
x*)
	commandPrefix="ssh $igor_host "
	;;
esac
case x$igor_script in
x)
	command="$commandPrefix python $dirKAKU/kaku"
	;;
x*)
	command="$commandPrefix python $igor_script"
	;;
esac
case x$igor_id in
x)
	echo Missing required argument id
	exit 1
	;;
esac
case x$igor_state in
xon|xTrue|xtrue|x1*)
	igor_state=on
	;;
x|xoff|xFalse|xfalse|x0*)
	igor_state=off
	;;
x*)
	echo Argument state=on or state=off required
	exit 1
	;;
esac
echo + $command $igor_state $igor_id
set
$command $igor_state $igor_id