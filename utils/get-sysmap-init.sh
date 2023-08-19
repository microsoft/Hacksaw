#!/bin/bash
#
# Copyright (c) 2022 Microsoft Corporation
# Licensed under the MIT License

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <System.map>"
	exit -1
fi

out=$(cat "$1" | grep '__initcall__kmod_')
if [ ! -z "$out" ]; then
	while IFS= read -r line; do
		f=$(echo $line | awk '{ print $3 }')
		p=$(echo "$f" | sed 's/__initcall__kmod_//g')
		e=$(echo "$p" | sed 's/early$//g')
		r=$(echo "$e" | sed 's/rootfs$//g')
		s=$(echo "$r" | sed 's/[1-7]s$//g')
		s2=$(echo "$s" | sed 's/[0-7]$//g')
		n=$(echo "$s2" | sed 's/__[0-9]*_[0-9]*_/\t/g')
		printf "$n\n"
	done <<< "$out"
fi
