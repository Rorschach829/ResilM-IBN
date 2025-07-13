#!/bin/bash
PYTHONPATH=. ryu-manager \
  --observe-links \
  ryu.app.ofctl_rest \
  ryu.app.rest_topology \
  ryu.topology.switches \
  backend/controller/PathIntentController.py \
  backend/controller/ryu_topology_rest.py \
  ryu.topology.switches \
  --ofp-tcp-listen-port 6633 \
  --ofp-listen-host 0.0.0.0 \
  --wsapi-port 8081 \
  # --verbose
  # ryu.app.simple_switch_stp_13 \
