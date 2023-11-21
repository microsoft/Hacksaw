#!/bin/bash

docker run -it --rm -v $PWD:/hacksaw -u $(id -u):$(id -g) hacksaw:0.1 /bin/bash -c "cd /hacksaw && ./driver_model/do-driver-model.sh"
