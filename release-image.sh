#!/bin/bash
TAG=$(cat VERSION)
docker build . -t infuseai/primehub-usage:$TAG
docker push infuseai/primehub-usage:$TAG
