FROM openeuler/openeuler:22.03-lts

WORKDIR /root

RUN dnf update -y && \
    dnf install -y \
    wget tar git make gcc gcc-c++ bison flex \
    glib2 glib2-devel libcap-ng-devel libattr-devel pixman-devel SDL2-devel \
    bzip2 cpio xz && \
    dnf clean all

RUN mkdir -p /root/source_code /root/qemu

COPY /downloads/qemu-5.0.0.tar.xz /root/source_code/
COPY /downloads/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu.tar.xz /root/source_code/
COPY /downloads/busybox-1.35.0.tar.bz2 /root/source_code/
COPY /downloads/kernel-22.09.tar.gz /root/source_code/
COPY /downloads/2048 /root/source_code/2048

# 1. Install QEMU
RUN cd /root/source_code && \
    tar -xvf qemu-5.0.0.tar.xz && \
    cd qemu-5.0.0 && \
    ./configure --target-list=aarch64-softmmu,arm-softmmu,aarch64-linux-user,arm-linux-user --enable-virtfs && \
    make -j$(nproc) && \
    make install

# 2. Install cross compiler
RUN cd /root/source_code && \
    tar -xvf gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu.tar.xz && \
    echo 'export PATH=/root/source_code/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu/bin:$PATH' >> /root/.bashrc

# 3. Compile Kernel
RUN cd /root/source_code && \
    tar -xzf kernel-22.09.tar.gz && \
    cd kernel && \
    # 显式设置 PATH 以确保交叉编译工具链可用
    export PATH=/root/source_code/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu/bin:$PATH && \
    make ARCH=arm64 openeuler_embedded_defconfig && \
    make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc) && \
    cp arch/arm64/boot/Image.gz /root/qemu/

# 4. Compile BusyBox
RUN cd /root/source_code && \
    tar -jxvf busybox-1.35.0.tar.bz2 && \
    cd busybox-1.35.0 && \
    export PATH=/root/source_code/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu/bin:$PATH && \
    make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig && \
    sed -i 's/# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config && \
    make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j$(nproc) && \
    make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- install

# 5. Build Rootfs
RUN mkdir -p /root/qemu/openEuler_embedded/rootfs/{home,lib} && \
    cp -af /root/source_code/busybox-1.35.0/_install/* /root/qemu/openEuler_embedded/rootfs/ && \
    cp -af /root/source_code/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu/aarch64-linux-gnu/libc/lib/*.so* /root/qemu/openEuler_embedded/rootfs/lib/ && \
    cp /root/source_code/2048 /root/qemu/openEuler_embedded/rootfs/bin/ && \
    export PATH=/root/source_code/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu/bin:$PATH && \
    # NOTE:||true
    aarch64-linux-gnu-strip /root/qemu/openEuler_embedded/rootfs/lib/* || true && \
    echo -e '#!/bin/sh\necho Welcome to mini_linux\nexec /bin/2048\nexec /bin/sh +m' > /root/qemu/openEuler_embedded/rootfs/init && \
    chmod +x /root/qemu/openEuler_embedded/rootfs/bin/2048 && \
    chmod +x /root/qemu/openEuler_embedded/rootfs/init && \
    cd /root/qemu/openEuler_embedded/rootfs && \
    find . -print0 | cpio --null -ov --format=newc | gzip -9 > /root/qemu/openEuler_embedded/rootfs.gz

# 6. Create QEMU shell script.
RUN echo -e '#!/bin/sh\n\
    export PATH=/root/source_code/gcc-linaro-7.5.0-2019.12-x86_64_aarch64-linux-gnu/bin:$PATH\n\
    qemu-system-aarch64 \\\n\
        -M virt-4.0 \\\n\
        -cpu cortex-a57 \\\n\
        -m 1G \\\n\
        -kernel /root/qemu/Image.gz \\\n\
        -initrd /root/qemu/openEuler_embedded/rootfs.gz \\\n\
        -nographic' > /root/qemu/openEuler_embedded/run-qemu.sh && \
    chmod +x /root/qemu/openEuler_embedded/run-qemu.sh

CMD ["/bin/bash"]
