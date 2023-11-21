FROM python:3.10.12-slim 

ARG USER_ID
ARG GROUP_ID

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
    bzip2 \
    gzip \
    lzop \
    lz4 \
    xz-utils \
    zstd \
  && pip install --upgrade pip \
  && pip install \
    z3-solver \
    kmax \
    psutil \
    pyelftools \
    capstone

RUN update-alternatives \
  --install /usr/bin/clang clang /usr/bin/clang-15 100 \
  --slave /usr/bin/clang++ clang++ /usr/bin/clang++-15 \
  --slave /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-15 \
  --slave /usr/bin/llvm-link llvm-link /usr/bin/llvm-link-15 \
  --slave /usr/bin/llvm-ar llvm-ar /usr/bin/llvm-ar-15 \
  --slave /usr/bin/opt opt /usr/bin/opt-15

RUN groupadd -g ${USER_ID} hacksaw
RUN useradd -u ${USER_ID} -g ${USER_ID} -m hacksaw

RUN mkdir -p /hacksaw
WORKDIR /hacksaw

COPY ./hacksaw.sh /
COPY ./prepare.sh /
COPY ./analyze.sh /
COPY ./patch.sh /
RUN chmod +x /*.sh
ENTRYPOINT ["/hacksaw.sh"]
