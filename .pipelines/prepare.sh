#!/bin/bash -e
# Copyright (c) 2023 Microsoft Corporation.
# Licensed under the MIT License.

set -x

sudo apt update
sudo apt install -y --no-install-recommends
sudo apt install -y \
	build-essential \
	clang-15 \
	make \
	cmake
