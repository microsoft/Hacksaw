#!/bin/bash

USERID=$(id -u)
GROUPID=$(id -g)

# docker buildx build -f Dockerfile -t hacksaw:0.1 --build-arg USER_ID=$USERID --build-arg GROUP_ID=$GROUPID .

pushd imager
docker buildx build -f Dockerfile -t hacksaw-imager:0.1 --build-arg USER_ID=$USERID --build-arg GROUP_ID=$GROUPID .
popd
