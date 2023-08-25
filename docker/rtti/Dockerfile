FROM hacksaw:0.1

ARG BUILD_PREFIX="/hacksaw-build"
ARG LLVM_SRC="${BUILD_PREFIX}/llvm-project-src"
ARG LLVM_BUILD="${BUILD_PREFIX}/llvm-build"
ARG LLVM_INSTALL="${BUILD_PREFIX}/llvm-install"
ARG LLVM_VER="15.0.7"

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
