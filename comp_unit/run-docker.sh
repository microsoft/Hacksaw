#!/bin/bash

docker build --tag comp_unit:0.1 .
docker run -it --rm -v $PWD:/mnt -u $(id -u):$(id -g) comp_unit:v1.0 sh -c "cd /mnt && ./test-comp-unit.sh"
