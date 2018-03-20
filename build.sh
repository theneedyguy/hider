#!/bin/bash
docker build . -t ckevi/hider:latest
docker tag ckevi/hider:latest ckevi/hider:1.4.1
docker push ckevi/hider:latest
docker push ckevi/hider:1.4.1
