#!/bin/bash
#
# Copyright (c) 2022 Microsoft Corporation
# Licensed under the MIT License

if [ "$#" -ne 2 ]; then
	echo "Usage: $0 <alias or file> <modules.builtin.modinfo>"
	exit -1
fi

if [ "$1" != "alias" ] && [ "$1" != "file" ]; then
	echo "Usage: $0 <alias or file> <modules.builtin.modinfo>"
	exit -1
fi

out=$(cat "$2" | sed 's/\x0/\n/g') 
if [ ! -z "$out" ]; then
	while IFS= read -r line; do
		ainfo=$(echo $line | grep "$1=")
		if [ ! -z "$ainfo" ]; then
			a=$(echo "$ainfo" | sed -E "s/.*\.$1=(.*)/\1/g")
			n=$(echo "$ainfo" | sed -E "s/(.*)\.$1=.*/\1/g")
			printf "$1 $a $n\n"
		fi
	done <<< "$out"
fi
