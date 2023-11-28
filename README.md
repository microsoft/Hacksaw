# Hacksaw

Hacksaw is a prototype toolkit to debloat Linux kernel based on hardware device inventory and dependency analysis. In particular, it customizes a given system disk image for a target hardware platform such as a cloud environment (e.g., an Azure VM) or a bare-metal machine. It was presented at [ACM CCS 2023](https://www.microsoft.com/en-us/research/publication/hacksaw-hardware-centric-kernel-debloating-via-device-inventory-and-dependency-analysis/).

## Usage

Hacksaw consists of numerous scripts and binaries managing its three main procedures: hardware database building, dependency analysis, and system image patching. We prepare Docker/Container environments to properly use them and a test script to run them in a proper order. For example, you can debloat a Ubuntu cloud image for a default QEMU-KVM environment like below:

```sh
$ pushd test
$ wget https://cloud-images.ubuntu.com/mantic/current/mantic-server-cloudimg-amd64.img
$ ./run.sh -b 1 -p hwprof/qemu-kvm.txt -i mantic-server-cloudimg-amd64.img
$ popd
```

The initial execution of `run.sh` could take several hours depending on your machine specification and require a lot of storage because it will compile Linux kernel 2-3 times. However, the hardware database and dependency analysis results can be reused later depending on (major) kernel version, kernel build configuration, and device inventory.

> Further instruction will be added later.

## CCS 2023 Artifact Evaluation

A version of Hacksaw for the CCS 2023 artifact evaluation can be found at
https://github.com/microsoft/hacksaw/tree/ccs23ae.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
