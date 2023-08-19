#!/bin/bash
#
# Copyright (c) 2022 Microsoft Corporation
# Licensed under the MIT License

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <module path>"
	exit -1
fi

for k in $(find "$1" -name "*.ko"); do
	out=$(modinfo -F firmware $k)
	if [ ! -z "$out" ]; then
		while IFS= read -r line; do
			printf "$(basename -s .ko $k)\t$line\n"
		done <<< "$out"
	fi
done
