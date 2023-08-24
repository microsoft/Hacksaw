FROM python:3.10.12-slim 
RUN apt update && apt install -y --no-install-recommends \
  && apt -y install gcc \
  && pip install z3-solver \
  && pip install kmax
