#!/bin/bash
#
# Copyright (c) 2022 Microsoft Corporation
# Licensed under the MIT License

if [ "$#" -ne 1 ]; then
	echo "Usage: $0 <initramfs>"
	exit -1
fi

file=$(realpath $1)
tempdir=$(mktemp -d)
mkdir -p out
outfilebase="$(realpath out)/$(basename $file)"

pushd $tempdir > /dev/null

cnt=0
while :
do
	cnt=$(( $cnt + 1 ))
	outfile=''
	blocks=''

	format=$(file $file | awk -F':' '{ print $2 }')
	if [[ $format == *"cpio"* ]]; then
		outfile="${outfilebase}-${cnt}.cpio"
	elif [[ $format == *"Zstandard"* ]]; then
		outfile="${outfilebase}-${cnt}.cpio.zst"
	elif [[ $format == *"gzip"* ]]; then
		outfile="${outfilebase}-${cnt}.cpio.gz"
	elif [[ $format == *"bzip2"* ]]; then
		outfile="${outfilebase}-${cnt}.cpio.bz2"
	elif [[ $format == *"XZ"* ]]; then
		outfile="${outfilebase}-${cnt}.cpio.xz"
	elif [[ $format == *"LZMA"* ]]; then
		outfile="${outfilebase}-${cnt}.cpio.lzma"
	elif [[ $format == *"LZ4"* ]]; then
		outfile="${outfilebase}-${cnt}.cpio.lz4"
	elif [[ $format == *"lzop"* ]]; then
		outfile="${outfilebase}-${cnt}.cpio.lzo"
	fi
	echo "$(basename $outfile)"

	if [[ $format == *"cpio"* ]]; then
		blocks=$(cpio -idv < $file 2>&1 | tail -n 1 | awk '{ print $1 }')
		dd if=$file of=$outfile count=${blocks} 2> /dev/null
	else
		cp $file $outfile
		break
	fi

	remaining=$(dd if=$file of="tmp-${cnt}" skip=$blocks 2>&1 | grep 'bytes' | awk '{ print $1 }')
	if [ -z "$remaining" ] || [ "$remaining" == "0" ]; then
		break
	fi
	file="tmp-${cnt}"
done

popd > /dev/null
