#!/bin/bash

docker build --tag comp_unit:v1.0 .
docker run -it --rm -v $PWD:/mnt -u $(id -u):$(id -g) comp_unit:v1.0 sh -c "cd /mnt && ./do-comp-unit.sh"
