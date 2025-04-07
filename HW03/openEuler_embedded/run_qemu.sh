#!/bin/sh
qemu-system-aarch64 \
    -M virt \
    -cpu cortex-a57 \
    -m 1G \
    -kernel Image.gz \
    -initrd rootfs.gz \
    -nographic \
