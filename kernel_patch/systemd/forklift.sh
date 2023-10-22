#!/bin/sh

main () {
    if [ ! -f /reboot_cnt ]; then
        echo 1 > /reboot_cnt;
    fi
    cnt=`cat /reboot_cnt`
    if [ $cnt -gt 10 ]; then
        echo "OUT";
        exit 0;
    fi
    #dmesg -d|grep "Run /init as init process" >> /dmesg_kernel
    #dmesg -d|grep "filesystem" >> /dmesg_fs_rd
    #dmesg -d|grep "systemd" >> /dmesg_sys_rd
    lsmod > /early_mod
    #free -h
    dmesg -d > /dmesg_$cnt
    cnt=$((cnt+1))
    echo $cnt > /reboot_cnt
    $(sleep 20; lsmod > /loaded_mod; systemd-analyze >> /boot_log 2>&1; systemd-analyze blame >> /boot_log 2>&1; slabtop -o|head -n 6 >> /boot_ram_log 2>&1; reboot -f) &
    #systemd-analyze >> /boot_log
    #reboot -f
}

main
exit 0
