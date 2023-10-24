#!/bin/bash

USERID=$(id -u)
GROUPID=$(id -g)

pushd builder
docker buildx build -f Dockerfile -t hacksaw-builder:0.1 --build-arg USER_ID=$USERID --build-arg GROUP_ID=$GROUPID .
popd

pushd patcher
docker buildx build -f Dockerfile -t hacksaw-patcher:0.1 --build-arg USER_ID=$USERID --build-arg GROUP_ID=$GROUPID .
popd
