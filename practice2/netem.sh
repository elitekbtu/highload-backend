#!/bin/sh
# Linux only (or a container with --cap-add=NET_ADMIN).
# usage: ./netem.sh delay | loss | del
DEV="${DEV:-eth0}"

case "$1" in
  delay) tc qdisc add dev "$DEV" root netem delay 100ms 10ms ;;
  loss)  tc qdisc add dev "$DEV" root netem delay 100ms 10ms loss 1% ;;
  del)   tc qdisc del dev "$DEV" root ;;
  *)     echo "usage: $0 delay|loss|del"; exit 1 ;;
esac
ping -c 3 127.0.0.1
