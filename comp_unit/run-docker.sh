#!/bin/bash

docker run -it --rm -v $PWD:/mnt -u $(id -u):$(id -g) hacksaw:0.1 sh -c "cd /mnt && ./test-comp-unit.sh"
