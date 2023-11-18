FROM debian:12.2-slim

ARG USER_ID
ARG GROUP_ID

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
RUN apt update \
  && apt install -y --no-install-recommends \
  && apt install -y \
    libguestfs-tools

RUN groupadd -g ${USER_ID} hacksaw
RUN useradd -u ${USER_ID} -g ${USER_ID} -m hacksaw

RUN mkdir -p /hacksaw
WORKDIR /hacksaw

COPY ./hacksaw.sh /
COPY ./extract.sh /
COPY ./update.sh /
RUN chmod +x /*.sh
ENTRYPOINT ["/hacksaw.sh"]
