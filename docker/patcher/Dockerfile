FROM python:3.10.12-slim 

ARG USER_ID
ARG GROUP_ID

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
RUN apt update \
  && apt install -y --no-install-recommends \
  && apt install -y \
    wget \
    libguestfs-tools \
  && pip install --upgrade pip \
  && pip install \
    psutil \
    pyelftools \
    capstone

RUN groupadd -g ${USER_ID} hacksaw
RUN useradd -u ${USER_ID} -g ${USER_ID} -m hacksaw

RUN mkdir -p /hacksaw
WORKDIR /hacksaw

COPY ./entrypoint.sh /
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
