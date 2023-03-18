#!/bin/bash

echo 'Running restarting script'

while true
do
  echo 'Start bot'
  python3 /root/bots/tg2vk/main.py &
  PID=$!
  sleep 28800 # Каждые 8 часов
  echo 'Kill bot'
  kill -KILL $PID
  echo
  echo
done
