#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

restart_delay=2

pids=()

run_loop() {
  local name="$1"
  local script="$2"
  while true; do
    echo "[$name] starting: $script"
    bash "$script"
    status=$?
    echo "[$name] exited with status $status. Restarting in ${restart_delay}s..."
    sleep "$restart_delay"
  done
}

cleanup() {
  echo "[supervisor] shutting down..."
  for pid in "${pids[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
    fi
  done
  wait
}
trap cleanup EXIT INT TERM

run_loop "rtdb_relay" "./rtdb_relay.sh" & pids+=($!)
run_loop "server" "./server.sh" & pids+=($!)
run_loop "pubsub_worker" "./pubsub_worker.sh" & pids+=($!)

echo "[supervisor] all processes started. Press Ctrl+C to stop."
wait
