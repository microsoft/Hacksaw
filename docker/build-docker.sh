#!/bin/bash

docker buildx build -f Dockerfile -t hacksaw:0.1 .

pushd rtti
docker buildx build -f Dockerfile -t hacksaw-rtti:0.1 .
popd
