#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
 Authors:
   yifengyou <842056007@qq.com>
"""
import glob
import os
import random
import re
import shutil
import subprocess
import sys
import argparse
import time

import select

CURRENT_VERSION = "0.2.0"
DEBUG = False

KERNEL_BUILD_MAP = {
    "linux-2.0": {
        "docker": [
            "dockerproxy.com/yifengyou/linux2.0:latest"
        ],
        "image":
            {
                "x86_64": {
                    "ubuntu": [
                        "http://cloud-images.ubuntu.com/releases/lucid/release-20150427/ubuntu-10.04-server-cloudimg-amd64-disk1.img"
                    ],
                    "debian": [],
                    "centos": [],
                    "fedora": [],
                },
                "arm64": {
                    "ubuntu": [
                        "http://cloud-images.ubuntu.com/releases/lucid/release-20150427/ubuntu-10.04-server-cloudimg-amd64-disk1.img",
                    ],
                    "debian": [],
                    "centos": [],
                    "fedora": [],
                }
            }
    },
    "linux-3.0": {
        "docker": [
            "dockerproxy.com/yifengyou/linux3.0:latest"
        ],
        "image":
            {
                "x86_64": {
                    "ubuntu": [
                        "http://cloud-images-archive.ubuntu.com/releases/precise/release-20170502/ubuntu-12.04-server-cloudimg-amd64-disk1.img",
                        "http://cloud-images.ubuntu.com/releases/trusty/release/ubuntu-14.04-server-cloudimg-amd64-disk1.img",
                        "http://cloud-images.ubuntu.com/releases/trusty/release/ubuntu-14.04-server-cloudimg-amd64-uefi1.img",
                    ],
                    "debian": [
                    ],
                    "centos": [],
                    "fedora": [],
                },
                "arm64": {
                    "ubuntu": [
                        "http://cloud-images.ubuntu.com/releases/trusty/release/ubuntu-14.04-server-cloudimg-arm64-disk1.img",
                        "http://cloud-images.ubuntu.com/releases/trusty/release/ubuntu-14.04-server-cloudimg-arm64-uefi1.img",
                    ],
                    "debian": [],
                    "centos": [],
                    "fedora": [],
                }
            }
    },
    "linux-4.0": {
        "docker": [
            "dockerproxy.com/yifengyou/linux4.0:latest"
        ],
        "image":
            {
                "x86_64": {
                    "ubuntu": [
                        "http://cloud-images.ubuntu.com/releases/bionic/release/ubuntu-18.04-server-cloudimg-amd64.img"
                    ],
                    "debian": [
                        "https://cloud.debian.org/images/cloud/buster/latest/debian-10-nocloud-amd64.qcow2",
                    ],
                    "centos": [],
                    "fedora": [],
                },
                "arm64": {
                    "ubuntu": [
                        "http://cloud-images.ubuntu.com/releases/bionic/release/ubuntu-18.04-server-cloudimg-arm64.img",
                    ],
                    "debian": [
                        "https://cloud.debian.org/images/cloud/bookworm/latest/debian-10-nocloud-arm64.qcow2",
                    ],
                    "centos": [],
                    "fedora": [],
                }
            }
    },
    "linux-5.0": {
        "docker": [
            "dockerproxy.com/yifengyou/linux5.0:latest"
        ],
        "image":
            {
                "x86_64": {
                    "ubuntu": [
                        "http://cloud-images.ubuntu.com//releases/focal/release/ubuntu-20.04-server-cloudimg-amd64.img",
                    ],
                    "debian": [
                        "https://cloud.debian.org/images/cloud/bullseye/latest/debian-11-nocloud-amd64.qcow2",
                    ],
                    "centos": [],
                    "fedora": [],
                },
                "arm64": {
                    "ubuntu": [
                        "http://cloud-images.ubuntu.com//releases/focal/release/ubuntu-20.04-server-cloudimg-arm64.img",
                    ],
                    "debian": [
                        "https://cloud.debian.org/images/cloud/bookworm/latest/debian-11-nocloud-arm64.qcow2",
                    ],
                    "centos": [],
                    "fedora": [],
                }
            }
    },
    "linux-6.0": {
        "docker": [
            "dockerproxy.com/yifengyou/linux6.0:latest"
        ],
        "image":
            {
                "x86_64": {
                    "ubuntu": [
                        "https://cloud-images.ubuntu.com/releases/jammy/release/ubuntu-22.04-server-cloudimg-amd64.img",
                    ],
                    "debian": [
                        "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-nocloud-amd64.qcow2",
                    ],
                    "centos": [],
                    "fedora": [],
                },
                "arm64": {
                    "ubuntu": [
                        "https://cloud-images.ubuntu.com/releases/jammy/release/ubuntu-22.04-server-cloudimg-arm64.img",
                    ],
                    "debian": [
                        "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-nocloud-arm64.qcow2",
                    ],
                    "centos": [],
                    "fedora": [],
                }
            }
    }
}


def check_python_version():
    current_python = sys.version_info[0]
    if current_python == 3:
        return
    else:
        raise Exception('Invalid python version requested: %d' % current_python)


def check_privilege():
    if os.getuid() == 0:
        return
    else:
        print("superuser root privileges are required to run")
        print(f"  sudo kdev {' '.join(sys.argv[1:])}")
        sys.exit(1)


def check_arch(args):
    print(" -> Step check environment")
    if args.arch:
        if args.arch == "x86_64":
            print("The target arch is x86_64")
        elif args.arch == "arm64":
            print("The target arch is arm64")
        else:
            print(f"Unsupported arch {args.arch}", file=sys.stderr)
            sys.exit(1)
    else:
        args.arch = os.uname().machine
        print(f"The target arch is {args.arch} (auto-detect)")


def check_src_hugefile(args):
    # github不支持直接推送100M+文件，尽量不要大文件
    ret, _, _ = do_exe_cmd(["find", args.sourcedir, "-name", ".git", "-prune", "-type", "f", "-size", "+100M"],
                           capture_output=True, text=True)
    if ret == 0:
        print("Warnning!find file large than 100MB")


def check_docker_image(args):
    linux_version = "linux-%s.0" % args.masterversion
    try:
        docker_img_list = KERNEL_BUILD_MAP[linux_version]["docker"]
    except KeyError:
        return False, ''
    if len(docker_img_list) == 0:
        return False, ''
    return True, docker_img_list[0]


def check_qcow_image(args):
    linux_version = "linux-%s.0" % args.masterversion
    try:
        qcow_img_list = KERNEL_BUILD_MAP[linux_version]["image"][args.arch]
    except KeyError:
        return False, ''
    if "debian" in qcow_img_list and len(qcow_img_list["debian"]) != 0:
        return True, qcow_img_list["debian"][0]
    elif "ubuntu" in qcow_img_list and len(qcow_img_list["ubuntu"]) != 0:
        return True, qcow_img_list["ubuntu"][0]
    elif "centos" in qcow_img_list and len(qcow_img_list["centos"]) != 0:
        return True, qcow_img_list["centos"][0]
    elif "fedora" in qcow_img_list and len(qcow_img_list["fedora"]) != 0:
        return True, qcow_img_list["fedora"][0]
    return False, ''


def do_exe_cmd(cmd, enable_log=False, logfile="build-kernel.log", print_output=False, shell=False):
    stdout_output = ''
    stderr_output = ''
    if isinstance(cmd, str):
        cmd = cmd.split()
    elif isinstance(cmd, list):
        pass
    else:
        raise Exception("unsupported type when run do_exec_cmd", type(cmd))
    if enable_log:
        log_file = open(logfile, "w+")
    pdebug("Run cmd:" + " ".join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
    while True:
        # 使用select模块，监控stdout和stderr的可读性，设置超时时间为0.1秒
        rlist, _, _ = select.select([p.stdout, p.stderr], [], [], 0.1)
        # 遍历可读的文件对象
        for f in rlist:
            # 读取一行内容，解码为utf-8
            line = f.readline().decode('utf-8').strip()
            # 如果有内容，判断是stdout还是stderr，并打印到屏幕，并刷新缓冲区
            if line:
                if f == p.stdout:
                    if print_output == True:
                        print("STDOUT", line)
                    if enable_log:
                        log_file.write(line + "\n")
                    stdout_output += line + '\n'
                    sys.stdout.flush()
                elif f == p.stderr:
                    if print_output == True:
                        print("STDERR", line)
                    if enable_log:
                        log_file.write(line + "\n")
                    stderr_output += line + '\n'
                    sys.stderr.flush()
        if p.poll() is not None:
            break

    # 关闭日志描述符
    if enable_log:
        log_file.close()

    return p.returncode, stdout_output, stderr_output


def do_clean_nbd():
    for entry in os.listdir("/sys/block/"):
        full_path = os.path.join("/sys/block/", entry)
        if os.path.isdir(full_path) and os.path.basename(full_path).startswith("nbd"):
            if os.path.exists(os.path.join(full_path, "pid")):
                nbd_name = os.path.basename(full_path)
                retcode, _, _ = do_exe_cmd(f"qemu-nbd -d /dev/{nbd_name}", print_output=True)
                if 0 != retcode:
                    print(f"umount {nbd_name} failed! retcode={retcode}")
                else:
                    print(f"umount {nbd_name} done!")


def perror(str):
    print("Error: ", str)
    sys.exit(1)


def pwarn(str):
    print("Warn: ", str)


def pdebug(params):
    global DEBUG
    if DEBUG:
        print("DEBUG:", params)


def handle_init(args):
    check_arch(args)
    deplist = "git  " \
              "wget  " \
              "vim " \
              "flex " \
              "bison " \
              "build-essential " \
              "tmux " \
              "qemu-system-x86 libvirt-clients libvirt-daemon-system bridge-utils virtinst libvirt-daemon virt-manager " \
              "openvswitch-common openvswitch-dev openvswitch-switch " \
              "firmware-misc-nonfree " \
              "ipxe-qemu " \
              "libvirt-daemon-driver-qemu " \
              "qemu " \
              "qemu-efi " \
              "qemu-efi-aarch64 " \
              "qemu-efi-arm " \
              "qemu-system " \
              "qemu-system-arm " \
              "qemu-system-common " \
              "qemu-system-data " \
              "qemu-system-gui:amd64 " \
              "qemu-system-mips " \
              "qemu-system-misc " \
              "qemu-system-ppc " \
              "qemu-system-sparc " \
              "qemu-system-x86 " \
              "qemu-user " \
              "qemu-user-binfmt " \
              "qemu-utils " \
              "sysstat " \
              "python3-pip " \
              "curl " \
              "docker-ce"
    ret, _, stderr = do_exe_cmd(f"sudo apt-get install -y {deplist}", print_output=True)
    if ret != 0:
        perror(f"install dependency failed! \n{stderr}")
    print("handle init done!")


def handle_check(args):
    check_arch(args)
    if not args.workdir:
        args.workdir = os.getcwd()
    print(f"workdir : {args.workdir}")

    if args.sourcedir:
        if not os.path.isdir(args.sourcedir):
            print(f"dir {args.sourcedir} does't exists!")
            sys.exit(1)
    else:
        args.sourcedir = os.getcwd()
        print(f"sourcedir is {args.sourcedir}")

    if os.path.isfile(os.path.join(args.sourcedir, "Makefile")) and \
            os.path.isfile(os.path.join(args.sourcedir, "Kbuild")):
        print(f"Check {args.sourcedir} ok! It's kernel source directory.")
    else:
        print(f"Check {args.sourcedir} failed! It's not a kernel source directory.")
        sys.exit(1)

    os.chdir(args.sourcedir)
    ret, kernelversion, _ = do_exe_cmd("make kernelversion")
    if ret != 0:
        perror(f"Unsupported {kernelversion}")

    args.kernelversion = kernelversion.strip()
    print(f"kernel version : {args.kernelversion}")

    args.masterversion = args.kernelversion[0]
    if args.masterversion not in [str(i) for i in range(1, 7)]:
        perror("unsupoorted masterversion", args.masterversion)
    print(f"master version : {args.masterversion}")

    print("handle check done!")


def handle_kernel(args):
    handle_check(args)
    print(" -> Step build kernel")
    os.chdir(args.workdir)

    if args.config:
        print(f" set kenrel config from cmdline {args.config}")
        kernel_config = args.config
    else:
        kernel_config = f"debian_{args.arch}_defconfig"

    # 生产编译脚本，因为不同环境对python版本有依赖要求，暂时不考虑规避，脚本万能
    body = """
    
## body

echo "run body"

cd ${SOURCEDIR}

mkdir -p ${WORKDIR}/build || :
make O=${WORKDIR}/build mrproper
make O=${WORKDIR}/build ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} """ + kernel_config + """

if [ $? -ne 0 ]; then
    echo "make  """ + kernel_config + """ failed!"
    exit 1
fi
ls -alh ${WORKDIR}/build/.config
make O=${WORKDIR}/build ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} -j "${JOB}"
if [ $? -ne 0 ]; then
    echo "Build kernel binary failed!"
    exit 1
fi

echo " kernel install to ${WORKDIR}/boot"
if [ ! -d "${WORKDIR}/boot" ]; then
    mkdir -p ${WORKDIR}/boot
fi
make O=${WORKDIR}/build ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} install INSTALL_PATH=${WORKDIR}/boot
if [ $? -ne 0 ]; then
    echo "make install to ${WORKDIR}/boot failed!"
    exit 1
fi

echo " kernel modules install to ${WORKDIR}"
make O=${WORKDIR}/build ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} INSTALL_MOD_STRIP=1 modules_install -j ${JOB} INSTALL_MOD_PATH=${WORKDIR}
if [ $? -ne 0 ]; then
    # try again
    make O=${WORKDIR}/build ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} INSTALL_MOD_STRIP=1 modules_install -j ${JOB} INSTALL_MOD_PATH=${WORKDIR}
    if [ $? -ne 0 ]; then
        echo "make modules_install to ${WORKDIR} failed!"
        exit 1
    fi
fi

cd ${SOURCEDIR}
KERNELRELEASE=$( make -s --no-print-directory O=${WORKDIR}/build ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} kernelrelease 2>/dev/null )
KERNEL_HEADER_INSTALL=${WORKDIR}/usr/src/linux-headers-${KERNELRELEASE}
echo " kernel headers install to ${KERNEL_HEADER_INSTALL}"
if [ ! -d "${KERNEL_HEADER_INSTALL}" ]; then
    mkdir -p ${KERNEL_HEADER_INSTALL}
fi
make O=${WORKDIR}/build ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} headers_install INSTALL_HDR_PATH=${KERNEL_HEADER_INSTALL}
if [ $? -ne 0 ]; then
    echo "make headers_install to ${WORKDIR} failed!"
    exit 1
fi

"""

    if args.nodocker:
        print("build kernel in host")

        args.cross_compile = ''
        if os.uname().machine != args.arch:
            if args.arch == "arm64":
                args.cross_compile = "aarch64-linux-gnu-"

        head = """
#!/bin/bash

if [ -f /.dockerenv ]; then
    echo "should run in host, not in docker"
    exit 1
fi

WORKDIR=%s
SOURCEDIR=%s
ARCH=%s
CROSS_COMPILE=%s
KERNEL_HEADER_INSTALL=%s
JOB=%s
""" % (
            args.workdir,
            args.sourcedir,
            args.arch,
            args.cross_compile,
            args.kernelversion,
            args.job,

        )
        with open("build_in_host.sh", "w") as script:
            script.write(head + body)

        os.chmod("build_in_host.sh", 0o755)
        host_cmd = "/bin/bash build_in_host.sh"
        print("run host build cmd:", host_cmd)
        ret, output, error = do_exe_cmd(host_cmd,
                                        print_output=True,
                                        enable_log=True,
                                        logfile="build_kernel_in_host.log")
        if ret != 0:
            perror("host build failed!")
        print("host build ok with 0 retcode")

    else:
        print("build kernel in docker")
        ok, image = check_docker_image(args)
        if not ok:
            perror("not useable docker image found!")
        print(f" using docker image : {image} ")
        args.docker_image = image

        args.cross_compile = ''
        if os.uname().machine != args.arch:
            if args.arch == "arm64":
                args.cross_compile = "aarch64-linux-gnu-"

        head = """#!/bin/bash
set -x

if [ ! -f /.dockerenv ]; then
    echo "should run in docker, not in host"
    exit 1
fi

WORKDIR=%s
SOURCEDIR=%s
ARCH=%s
CROSS_COMPILE=%s
KERNEL_HEADER_INSTALL=%s
JOB=%s

""" % (
            "/work",
            "/kernel",
            args.arch,
            args.cross_compile,
            args.kernelversion,
            args.job,
        )
        with open("build_in_docker.sh", "w") as script:
            script.write(head + body)
        os.chmod("build_in_docker.sh", 0o755)
        docker_cmd = f"docker run -t  " \
                     f" -v {args.workdir}/build_in_docker.sh:/bin/kdev   " \
                     f" -v {args.sourcedir}:/kernel   " \
                     f" -v {args.workdir}:/workdir   " \
                     f" -w /workdir   " \
                     f"{args.docker_image}  " \
                     f"/bin/kdev"
        print("run docker build cmd:", docker_cmd)
        ret, output, error = do_exe_cmd(docker_cmd,
                                        print_output=True,
                                        shell=False,
                                        enable_log=True,
                                        logfile="build_kernel_in_docker.log")
        if ret != 0:
            perror(f"docker build failed! retcode={ret}")
        else:
            print("docker build ok with 0 retcode, exit docker.")

    print("handle kernel done!")


def handle_rootfs(args):
    handle_check(args)
    ok, image_url = check_qcow_image(args)
    if not ok:
        perror(" no available image found!")
    print(f" using qcows url {image_url}")

    args.qcow2_url = image_url
    args.qcow2 = os.path.basename(image_url)
    print(f" qcow2 name : {args.qcow2}")
    os.chdir(args.workdir)
    if not os.path.isfile(args.qcow2):
        print(f" start to download {args.qcow2_url}")
        retcode, _, _ = do_exe_cmd(["wget", "-c", args.qcow2_url],
                                   print_output=True,
                                   enable_log=True,
                                   logfile="kdev-download.log"
                                   )
        if retcode != 0:
            perror("Download qcow2 failed!")
    else:
        print(f" already exists {args.qcow2}, reusing it.")
        do_exe_cmd(["qemu-nbd", "--disconnect", args.qcow2], print_output=True)
        do_exe_cmd(["modprobe", "nbd", "max_part=19"], print_output=True)

    # 如果参数或配置指定了nbd，则使用，否则挨个测试
    if hasattr(args, 'nbd') and args.nbd is not None:
        do_exe_cmd(f"qemu-nbd --disconnect {os.path.join('/dev/', args.nbd)}", print_output=True)
        pdebug(f"try umount nbd /dev/{args.nbd}")
        retcode, _, _ = do_exe_cmd(["qemu-nbd", "--connect", os.path.join("/dev/", args.nbd), args.qcow2],
                                   print_output=True)
        if retcode != 0:
            perror("Connect nbd failed!")
    else:
        for nbd in ["nbd" + str(i) for i in range(9)]:
            retcode, output, error = do_exe_cmd(
                ["qemu-nbd", "--connect", "/dev/" + nbd,
                 args.qcow2],
                print_output=True)
            if retcode == 0:
                args.nbd = nbd
                break
        if not hasattr(args, 'nbd'):
            perror("No available nbd found!")

    # 稍作延迟
    do_exe_cmd("sync")

    # 创建临时挂载点
    args.tmpdir = "/tmp/qcow2-" + str(random.randint(0, 9999))
    os.makedirs(args.tmpdir, exist_ok=True)
    retcode, _, _ = do_exe_cmd(f"mount -o rw /dev/{args.nbd}p1 {args.tmpdir}", print_output=True)
    if retcode != 0:
        perror("Mount qcow2 failed!")

    # 稍作延迟
    do_exe_cmd("sync")

    # 拷贝boot目录，包含linux vmlinuz config maps
    copy_bootdir = os.path.join(args.workdir, "boot")
    qcow_bootdir = os.path.join(args.tmpdir, "boot")
    if os.path.isdir(copy_bootdir) and qcow_bootdir != "/boot":
        copy_cmd = ["/usr/bin/cp", "-a"] + glob.glob(f"{copy_bootdir}/*") + [f"{qcow_bootdir}/"]
        retcode, _, error = do_exe_cmd(copy_cmd)
        if retcode == 0:
            print(f" copy vmlinuz/config ok! {qcow_bootdir}")
        else:
            perror(f" copy vmlinuz/config failed!! {qcow_bootdir} {error}")

    # 稍作延迟
    do_exe_cmd("sync")

    # 拷贝lib目录，包含inbox核外驱动
    copy_libdir = os.path.join(args.workdir, "lib/modules")
    qcow_libdir = os.path.join(args.tmpdir, "lib/modules")
    if os.path.isdir(copy_libdir) and qcow_libdir != "/lib/modules":
        copy_cmd = ["/usr/bin/cp", "-a"] + glob.glob(f"{copy_libdir}/*") + [f"{qcow_libdir}/"]
        retcode, _, _ = do_exe_cmd(copy_cmd)
        if retcode == 0:
            print(f" copy modules(stripped) ok! {qcow_libdir}")
        else:
            perror(f" copy modules(stripped) failed!! {qcow_libdir}")

    # 稍作延迟
    do_exe_cmd("sync")

    # 拷贝内核头文件
    copy_headerdir = os.path.join(args.workdir, "usr")
    qcow_headerdir = os.path.join(args.tmpdir, "usr")
    if os.path.isdir(copy_headerdir) and qcow_headerdir != "/usr":
        copy_cmd = ["/usr/bin/cp", "-a"] + glob.glob(f"{copy_headerdir}/*") + [f"{qcow_headerdir}/"]
        retcode, _, _ = do_exe_cmd(copy_cmd)
        if retcode == 0:
            print(f" copy headers ok! {qcow_headerdir}")
        else:
            perror(f" copy headers failed!! {qcow_headerdir}")

    # 稍作延迟
    do_exe_cmd("sync")

    # 设置主机名
    args.hostname = args.qcow2.split(".")[0]
    qcow_hostname = os.path.join(args.tmpdir, "etc/hostname")
    with open(qcow_hostname, "w") as f:
        f.write(args.hostname.strip())
    print(f" set hostname : {args.hostname}")

    # 检查cloud-init变关闭
    qcow_cloudinitdir = os.path.join(args.tmpdir, "etc/cloud")
    if os.path.isdir(qcow_cloudinitdir):
        with open(os.path.join(qcow_cloudinitdir, "cloud-init.disabled"), "w") as f:
            f.write("")
    if os.path.isfile(os.path.join(args.tmpdir, "usr/bin/cloud-*")):
        pdebug("remove /usr/bin/cloud-*")
        os.remove(os.path.join(args.tmpdir, "usr/bin/cloud-*"))

    TMP_USRBIN = os.path.join(args.tmpdir, "usr/bin/")
    for item in os.listdir(TMP_USRBIN):
        if item.startswith("cloud-"):
            new_item = "bak-" + item
            os.rename(os.path.join(TMP_USRBIN, item), os.path.join(TMP_USRBIN, new_item))
            print(f"Renamed {item} to {new_item}")

    # 写入初始化脚本，开机第一次执行
    with open(os.path.join(args.tmpdir, "etc/firstboot"), "w") as f:
        f.write("")
    with open(os.path.join(args.tmpdir, "etc/rc.local"), "w") as f:
        f.write("""#!/bin/bash

if [ -f /etc/firstboot ]; then
	rm -f /etc/firstboot
	cd /boot
	for k in $(ls vmlinuz-*); do
		KERNEL=${k//vmlinuz-/}
		update-initramfs -k ${KERNEL} -c
	done
	if which update-grub2 &> /dev/null ; then
	    update-grub2
	fi
	sync
	if which chpasswd &> /dev/null ; then
		echo root:linux | chpasswd
	elif which passwd &> /dev/null ; then
		echo linux | passwd -stdin root
	else
		echo "can't reset root passwd"
	fi
	if [ -d /etc/cloud/ ]; then
		touch /etc/cloud/cloud-init.disabled
		rm -f /usr/bin/cloud-*
	fi
	if which ssh-keygen &> /dev/null ; then
	    ssh-keygen -A
	fi
	sync
	reboot -f
fi

exit 0

""")
    os.chmod(os.path.join(args.tmpdir, "etc/rc.local"), 0o755)
    print(" set rc.local done!")
    print(" clean ...")
    retcode, _, _ = do_exe_cmd(f"umount -l {args.tmpdir}", print_output=True)
    if retcode != 0:
        print("Umount failed!")
    retcode, _, _ = do_exe_cmd(f"qemu-nbd --disconnect /dev/{args.nbd}", print_output=True)
    if retcode != 0:
        print("Disconnect nbd failed!")
    os.rmdir(args.tmpdir)
    print("handle rootfs done!")


def handle_run(args):
    handle_check(args)
    if args.arch == "x86_64":
        args.qemuapp = "qemu-system-x86_64"
    elif args.arch == "arm64":
        args.qemuapp = "qemu-system-aarch64"
    else:
        perror(f"unsupported arch {args.arch}")

    path = shutil.which(args.qemuapp)
    # 判断路径是否为None，输出结果
    if path is None:
        print(f"{args.qemuapp} is not found in the system.")
        print("")
    else:
        print(f"{args.qemuapp} is found in the system at {path}.")

    path = shutil.which("virsh")
    # 判断路径是否为None，输出结果
    if path is None:
        print(f"virsh is not found in the system.")
        print("")
    else:
        print(f"virsh is found in the system at {path}.")

    # 检查是否有可用的QCOW2文件
    ok, image_url = check_qcow_image(args)
    if not ok:
        perror(" no available image found!")
    print(f" using qcows url {image_url}")

    args.qcow2_url = image_url
    args.qcow2 = os.path.basename(image_url)
    print(f" qcow2 name : {args.qcow2}")

    os.chdir(args.workdir)
    if not os.path.isfile(args.qcow2):
        print(" no qcow2 found!")
        print("Tips: run `kdev rootfs`")
        sys.exit(1)
    else:
        print(f" found qcow2 {args.qcow2} in workdir, using it.")

    if not hasattr(args, "name") or args.name is None:
        args.name = f"linux-{args.masterversion}-{args.arch}"

    print(f" try startup {args.name}")
    retcode, args.vmstat, _ = do_exe_cmd(f"virsh domstate {args.name}", print_output=False)
    if 0 == retcode:
        if args.vmstat.strip() == "running":
            print(f"{args.name} already running")
            return
        ret, _, _ = do_exe_cmd(f"virsh start {args.name}", print_output=True)
        if 0 == ret:
            print(f"start vm {args.name} ok, enjoy it.")
        else:
            perror(f"start vm {args.name} failed,check it.")
        sys.exit(0)

    print(f" {args.name} does't exists! create new vm")

    if args.arch == "x86_64":
        args.vmarch = "x86_64"
        if not args.vmcpu:
            args.vmcpu = "8"
        if not args.vmram:
            args.vmram = "8192"
    elif args.arch == "arm64":
        args.vmarch = "aarch64"
        if not args.vmcpu:
            args.vmcpu = "2"
        if not args.vmram:
            args.vmram = "4096"
    else:
        perror(f"unsupported arch {args.arch}")

    qemu_cmd = f"virt-install  " \
               f"  --name {args.name} " \
               f"  --arch {args.vmarch} " \
               f"  --ram {args.vmram} " \
               f"  --os-type=linux " \
               f"  --video=vga " \
               f"  --vcpus {args.vmcpu}  " \
               f"  --disk path={os.path.join(args.workdir, args.qcow2)},format=qcow2,bus=scsi " \
               f"  --network bridge=br0,virtualport_type=openvswitch " \
               f"  --import " \
               f"  --graphics spice,listen=0.0.0.0 " \
               f"  --noautoconsole"

    retcode, _, _ = do_exe_cmd(qemu_cmd, print_output=True)
    if 0 == retcode:
        print(f" start {args.name} success! enjoy it~~")
    else:
        print(f" start {args.name} failed!")
    print("handle run done!")


def handle_clean(args):
    handle_check(args)
    # 清理虚拟机配置，保留qcow2
    if args.vm or args.all:
        if not hasattr(args, "name"):
            args.name = f"linux-{args.masterversion}-{args.arch}"
        retcode, _, _ = do_exe_cmd(f"virsh domstate {args.name}", print_output=False)
        if 0 == retcode:
            retcode, _, _ = do_exe_cmd(f"virsh destroy {args.name}", print_output=True)
            if 0 == retcode:
                print(f" destroy vm {args.name} ok")
            else:
                print(f" destroy vm {args.name} failed!")
            retcode, _, _ = do_exe_cmd(f"virsh undefine {args.name}", print_output=True)
            if 0 == retcode:
                print(f" undefine vm {args.name} ok")
            else:
                print(f" undefine vm {args.name} failed!")
        else:
            print(f"no vm {args.name} found! skip clean vm.")
    # 清理qcow2，保留虚机配置
    if args.qcow or args.all:
        os.chdir(args.workdir)
        for filename in os.listdir('.'):
            if filename.endswith(".qcow2"):
                pdebug(f" Find qcow2 {filename}")
                filepath = os.path.join(args.workdir, filename)
                os.remove(filepath)
                print(f"Deleted {filepath}")
    if args.docker or args.all:
        retcode, _, _ = do_exe_cmd(f"docker container prune -f", print_output=True)
        if 0 == retcode:
            print("clean docker container done!")
        else:
            print(f"clean docker container failed! retcode={retcode}")

    print("handle clean done!")


def handle_image(args):
    check_privilege()

    # 定义一个函数，判断一个路径是否是nbd开头的目录
    def is_nbd_dir(path):
        return os.path.isdir(path) and os.path.basename(path).startswith("nbd")

    def find_free_nbd():
        for entry in os.listdir("/sys/block/"):
            full_path = os.path.join("/sys/block/", entry)
            if is_nbd_dir(full_path):
                if not os.path.exists(os.path.join(full_path, "pid")):
                    return os.path.basename(full_path)
        return ''

    if args.mount:
        print("mount file :", args.mount)
        # 检查文件是否存在
        if os.path.isfile(args.mount):
            # 获取文件的绝对路径
            file = os.path.abspath(args.mount)

            nbd = find_free_nbd()
            if '' == nbd:
                perror("no available /dev/nbd found!")
            print(f"try mount {file} to /dev/{nbd}")
            ok, _, _ = do_exe_cmd(f"qemu-nbd -c /dev/{nbd} {file}", print_output=True)
            if 0 != ok:
                perror(f"qemu-nbd bind {file} failed! retcode={ok}")
            else:
                print(f"qemu-nbd bind {file} done!")
            mntdir = file + '-mnt'
            os.makedirs(mntdir, exist_ok=True)
            time.sleep(3)
            ok, _, _ = do_exe_cmd(f"mount /dev/{nbd}p1 {mntdir}", print_output=True)
            if 0 != ok:
                perror(f"mount {file} failed! retcode={ok}")
            else:
                print(f"mount {args.mount} to {mntdir} done!")
        else:
            # 打印错误信息
            print(f"File {args.umount} does not exist")
    elif args.umount:
        print("umount file :", args.umount)
        # 检查文件是否存在
        if os.path.isfile(args.umount):
            # 获取文件的绝对路径
            file = os.path.abspath(args.umount)
            # 获取挂载目录的绝对路径
            mnt_dir = file + "-mnt"
            if os.path.isdir(mnt_dir):
                retcode, _, _ = do_exe_cmd(f"umount {mnt_dir}")
                time.sleep(1)
                print(f"try umount {file} ret={retcode}")
                if len(os.listdir(mnt_dir)) != 0:
                    perror(f"{mnt_dir} is not empty! umount failed! keep mount dir empty!")
                print(f"{mnt_dir} is already empty!")
            # disconnect nbd
            do_clean_nbd()
        else:
            # 打印错误信息
            print(f"File {args.umount} does not exist")


def main():
    global DEBUG, CURRENT_VERSION
    check_python_version()

    # 顶层解析
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--version", action="store_true",
                        help="show program's version number and exit")
    parser.add_argument("-h", "--help", action="store_true",
                        help="show this help message and exit")
    subparsers = parser.add_subparsers()

    # 定义base命令用于集成
    parent_parser = argparse.ArgumentParser(add_help=False, description="kdev - a tool for kernel development")
    parent_parser.add_argument("-V", "--verbose", default=None, action="store_true", help="show verbose output")
    parent_parser.add_argument("-s", "--sourcedir", default=None, help="set kernel source dir")
    parent_parser.add_argument("-a", "--arch", default=None, help="set arch, default is x86_64")
    parent_parser.add_argument("-w", "--workdir", default=None, help="setup workdir")
    parent_parser.add_argument('-l', '--log', default=None, help="log file path")
    parent_parser.add_argument('-d', '--debug', default=None, action="store_true", help="enable debug output")

    # 添加子命令 init
    parser_init = subparsers.add_parser('init', parents=[parent_parser])
    parser_init.set_defaults(func=handle_init)

    # 添加子命令 check
    parser_check = subparsers.add_parser('check', parents=[parent_parser])
    parser_check.set_defaults(func=handle_check)

    # 添加子命令 kernel
    parser_kernel = subparsers.add_parser('kernel', parents=[parent_parser])
    parser_kernel.add_argument("--nodocker", default=None, action="store_true",
                               help="build kernel without docker environment")
    parser_kernel.add_argument("-j", "--job", default=os.cpu_count(), help="setup compile job number")
    parser_kernel.add_argument("-c", "--clean", help="clean docker when exit")
    parser_kernel.add_argument("--config", help="setup kernel build config")
    parser_kernel.set_defaults(func=handle_kernel)

    # 添加子命令 rootfs
    parser_rootfs = subparsers.add_parser('rootfs', parents=[parent_parser])
    parser_rootfs.add_argument('-r', '--release', default=None, action="store_true")
    parser_rootfs.set_defaults(func=handle_rootfs)

    # 添加子命令 run
    parser_run = subparsers.add_parser('run', parents=[parent_parser])
    parser_run.add_argument('-n', '--name', help="setup vm name")
    parser_run.add_argument('--vmcpu', help="setup vm vcpu number")
    parser_run.add_argument('--vmram', help="setup vm ram")
    parser_run.set_defaults(func=handle_run)

    # 添加子命令 clean
    parser_clean = subparsers.add_parser('clean', parents=[parent_parser])
    parser_clean.add_argument('--vm', default=None, action="store_true", help="clean vm (destroy/undefine)")
    parser_clean.add_argument('--qcow', default=None, action="store_true", help="delete qcow")
    parser_clean.add_argument('--docker', default=None, action="store_true", help="clean docker")
    parser_clean.add_argument('--all', default=None, action="store_true", help="clean all")
    parser_clean.set_defaults(func=handle_clean)

    # 添加子命令 image
    parser_image = subparsers.add_parser('image')
    # 添加一个互斥组，用于指定-u或-m参数，但不能同时指定
    parser_image_group = parser_image.add_mutually_exclusive_group(required=True)
    parser_image_group.add_argument('-m', '--mount', metavar='QCOW2_FILE_PATH', help="mount qcow2")
    parser_image_group.add_argument('-u', '--umount', metavar='QCOW2_FILE_PATH', help="umount qcow2")
    parser_image_group.set_defaults(func=handle_image)

    # 开始解析命令
    args = parser.parse_args()

    # 解析命令后解析配置文件，合并两者
    for filename in os.listdir('.'):
        if filename.endswith(".kdev"):
            pdebug("load config file %s" % filename)
            with open(filename, 'r', encoding='utf8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    match = re.match(r'(\w+)\s*=\s*([\w/.-]+)', line)
                    if match:
                        key = match.group(1)
                        value = match.group(2)
                        # 如果命令行没有定义key，则使用配置中的KV
                        if not hasattr(args, key):
                            setattr(args, key, value)
                        # 如果命令行未打开选项，但配置中打开，则使用配置中的KV
                        if getattr(args, key) is None:
                            setattr(args, key, value)

    # 参数解析后开始具备debug output能力
    if hasattr(args, "debug") and args.debug is not None:
        DEBUG = True
        pdebug("Enable debug output")
    pdebug("Parser and config:")
    for key, value in vars(args).items():
        pdebug("  %s = %s" % (key, value))

    if args.version:
        print("kdev %s" % CURRENT_VERSION)
        sys.exit(0)
    elif args.help or len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
