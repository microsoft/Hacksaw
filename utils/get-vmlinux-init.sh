#!/bin/bash
#
# Copyright (c) 2022 Microsoft Corporation
# Licensed under the MIT License

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <vmlinux>"
	exit -1
fi

out=$(objdump -t -j.init.data -j.init.text -j.text "$1")
if [ ! -z "$out" ]; then
	initfn=""
	while IFS= read -r line; do
		c=$(echo $line | grep "__initcall__kmod_")
		if [ ! -z "$c" ]; then
			initfn="$c"
		else
			if [ "$initfn" != "" ]; then
				t=$(echo $initfn | awk '{ print $5 }')
				t2=$(echo "$t" | sed -E 's/^__initcall__kmod_(.*)__[0-9]*_[0-9]*_.*/\1/g')
				n=$(echo $line | awk '{ print $6 }')
				printf "$t2\t$n\n"
			fi
			initfn=""
		fi
	done <<< "$out"
fi
