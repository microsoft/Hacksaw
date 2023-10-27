#!/bin/bash

pushd ./docker

./build-docker.sh

popd

./driver_model/run-docker.sh
./comp_unit/docker-run.sh
./hwdb/run-docker.sh
