#!/bin/bash
#
# Copyright (c) 2022 Microsoft Corporation
# Licensed under the MIT License

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <module path>"
	exit -1
fi

for k in $(find "$1" -name "*.ko"); do
	dump=$(objdump -t $k | grep "F\s\(\|.init\).text\(\|.early\)")
	out=$(printf "$dump" | grep "\sinit_module$")
	initfn="NOINIT"
	if [ ! -z "$out" ]; then
		arr=($(echo $out | awk '{ print $1, $4, $5 }'))
 		out=$(printf "$dump" | grep "F\s${arr[1]}\s" | grep "${arr[0]}" | grep "${arr[2]}")
		if [ ! -z "$out" ]; then
			while IFS= read -r line; do
				n=$(echo $line | awk '{ print $6 }')
				if [ "$n" != "init_module" ]; then
					initfn=$n
					break
				fi
			done <<< "$out"
		else
			initfn="FAILED"
		fi
	fi
	printf "$(basename -s .ko $k)\t$initfn\n"
done
