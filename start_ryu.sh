#!/bin/bash
PYTHONPATH=. ryu-manager \
  --observe-links \
  ryu.app.ofctl_rest \
  ryu.app.simple_switch_stp_13 \
  --ofp-tcp-listen-port 6633 \
  --ofp-listen-host 0.0.0.0 \
  --wsapi-port 8081 \
  # --verbose

