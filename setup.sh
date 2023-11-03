#!/bin/bash

pushd ./docker

./build-docker.sh

popd

./driver_model/run-docker.sh
./comp_unit/run-docker.sh
./hwdb/run-docker.sh
