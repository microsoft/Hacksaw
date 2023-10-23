#!/bin/bash

UID=$(id -u)
GID=$(id -g)

pushd builder
docker buildx build -f Dockerfile -t hacksaw-builder:0.1 --build-arg USER_ID=$UID --build-arg GROUP_ID=$GID .
popd

pushd patcher
docker buildx build -f Dockerfile -t hacksaw-patcher:0.1 --build-arg USER_ID=$UID --build-arg GROUP_ID=$GID .
popd
