FROM python:3.10.12-slim 
RUN apt update && apt install -y --no-install-recommends \
  && apt -y install build-essential \
  && apt -y install libncurses-dev \
  && apt -y install bison \
  && apt -y install flex \
  && apt -y install libssl-dev \
  && apt -y install libelf-dev \
  && apt -y install cmake \
  && apt -y install file \
  && apt -y install bc \
  && apt -y install cpio \
  && apt -y install clang-15 \
  && pip install --upgrade pip \
  && pip install wllvm
RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-15 100
RUN update-alternatives --install /usr/bin/llvm-link llvm-link /usr/bin/llvm-link-15 100
