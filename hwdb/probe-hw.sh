#!/bin/bash
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

find "/sys/devices" -name "modalias" -exec cat {} \; | sort | uniq
