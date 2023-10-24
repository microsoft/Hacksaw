FROM python:3.10.12-slim 

ARG USER_ID
ARG GROUP_ID

ARG BUILD_PREFIX="/hacksaw-build"
ARG LLVM_SRC="${BUILD_PREFIX}/llvm-project-src"
ARG LLVM_BUILD="${BUILD_PREFIX}/llvm-build"
ARG LLVM_INSTALL="${BUILD_PREFIX}/llvm-install"
ARG LLVM_VER="15.0.7"

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
RUN apt update \
  && apt install -y --no-install-recommends \
  && apt install -y \
    build-essential \
    libncurses-dev \
    bison \
    flex \
    libssl-dev \
    libelf-dev \
    make \
    cmake \
    file \
    bc \
    cpio \
    clang-15 \
    wget \
    kmod \
  && pip install --upgrade pip \
  && pip install \
    z3-solver \
    kmax

RUN update-alternatives \
  --install /usr/bin/clang clang /usr/bin/clang-15 100 \
  --slave /usr/bin/clang++ clang++ /usr/bin/clang++-15 \
  --slave /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-15 \
  --slave /usr/bin/llvm-link llvm-link /usr/bin/llvm-link-15 \
  --slave /usr/bin/llvm-ar llvm-ar /usr/bin/llvm-ar-15 \
  --slave /usr/bin/opt opt /usr/bin/opt-15

RUN mkdir -p ${LLVM_SRC} \
  && mkdir -p ${LLVM_BUILD} \
  && mkdir -p ${LLVM_INSTALL} \
  && wget -c https://github.com/llvm/llvm-project/releases/download/llvmorg-${LLVM_VER}/llvm-project-${LLVM_VER}.src.tar.xz -O - | tar -xJ --strip-components=1 -C ${LLVM_SRC} \
  && cmake -G "Unix Makefiles" \
    -DCMAKE_BUILD_TYPE="Release" \
    -DLLVM_ENABLE_RTTI=On \
    -DBUILD_SHARED_LIBS=On \
    -DLLVM_ENABLE_DUMP=On \
    -DLLVM_TARGETS_TO_BUILD=X86 \
    -DLLVM_ENABLE_PROJECTS="clang" \
    -DCMAKE_INSTALL_PREFIX="${LLVM_INSTALL}" \
    -S ${LLVM_SRC}/llvm \
    -B ${LLVM_BUILD} \
  && cd ${LLVM_BUILD} \
  && make -j$(nproc) LLVMCore LLVMSupport LLVMIRReader \
  && make install-LLVMAsmParser \
  && make install-LLVMBinaryFormat \
  && make install-LLVMBitReader \
  && make install-LLVMBitstreamReader \
  && make install-LLVMCore \
  && make install-LLVMDemangle \
  && make install-LLVMIRReader \
  && make install-LLVMRemarks \
  && make install-LLVMSupport \
  && make install-LLVMTableGen \
  && make install-LLVMTableGenGlobalISel \
  && make install-llvm-headers \
  && cd ${BUILD_PREFIX} \
  && rm -rf ${LLVM_SRC} ${LLVM_BUILD}

RUN groupadd -g ${USER_ID} hacksaw
RUN useradd -u ${USER_ID} -g ${USER_ID} -m hacksaw

RUN mkdir -p /hacksaw
WORKDIR /hacksaw

COPY ./entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
