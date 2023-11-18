#!/bin/bash
#
# Copyright (c) 2023 Microsoft Corporation
# Licensed under the MIT License

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <rootpath>"
	exit 1
fi

ROOTPATH=$(realpath "$1")
BOOTPATH="${ROOTPATH}/boot"
MODPATH="${ROOTPATH}/lib/modules"

if [[ "$MODPATH" = "" ]]
then
	echo "$1/lib/modules does not exist."
	exit 1
fi

array=($(ls $MODPATH 2>/dev/null))
IFS=$'\n' sorted=($(sort -r <<<"${array[*]}"))
unset IFS
versig=${sorted[0]}

array=($(ls $BOOTPATH/*$versig* 2>/dev/null))
for value in "${array[@]}"
do
	valbase=$(basename $value)
	if [[ $valbase = vmlinuz* ]]; then
		vmlinuz=$value
	elif [[ $valbase = config* ]]; then
		config=$value
	elif [[ $valbase = System.map* ]]; then
		sysmap=$value
	elif [[ $valbase = initr* ]]; then
		initrd=$value
	fi
done

if [ -z "$vmlinuz" ]; then
	array=($(ls $BOOTPATH/vmlinuz* 2>/dev/null))
	IFS=$'\n' sorted=($(sort -r <<<"${array[*]}"))
	unset IFS
	vmlinuz=${sorted[0]}
	[[ -z "$vmlinuz" ]] && vmlinuz="none"
fi

if [ -z "$config" ]; then
	array=($(ls $BOOTPATH/config* 2>/dev/null))
	IFS=$'\n' sorted=($(sort -r <<<"${array[*]}"))
	unset IFS
	config=${sorted[0]}
	[[ -z "$config" ]] && config="none"
fi

if [ -z "$sysmap" ]; then
	array=($(ls $BOOTPATH/System.map* 2>/dev/null))
	IFS=$'\n' sorted=($(sort -r <<<"${array[*]}"))
	unset IFS
	sysmap=${sorted[0]}
	[[ -z "$sysmap" ]] && sysmap="none"
fi

if [ -z "$initrd" ]; then
	array=($(ls $BOOTPATH/initr* 2>/dev/null))
	IFS=$'\n' sorted=($(sort -r <<<"${array[*]}"))
	unset IFS
	initrd=${sorted[0]}
	[[ -z "$initrd" ]] && initrd="none"
fi

version=$(echo $versig | awk -F'-' '{ print $1 }')
version=${version%".0"}

echo "versig: $versig"
echo "version: $version"
echo "kernel: $vmlinuz"
echo "config: $config"
echo "sysmap: $sysmap"
echo "initramfs: $initrd"
