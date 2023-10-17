#!/bin/bash

docker run -it --rm -v $PWD:/mnt -u $(id -u):$(id -g) hacksaw:0.1 /bin/bash
