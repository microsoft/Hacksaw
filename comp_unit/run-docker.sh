#!/bin/bash
set -e

docker run -it --rm -v $PWD:/hacksaw -u $(id -u):$(id -g) hacksaw:0.1 /bin/bash -c "cd /hacksaw && ./comp_unit/do-comp-unit.sh"
