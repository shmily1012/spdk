# queue_depth_burst

The `queue_depth_burst` example issues a single burst of NVMe commands across a
configurable number of I/O queue pairs. Each queue is primed with commands that
start at a base LBA and advance by a fixed stride before the submission queue
doorbell is rung once to dispatch the full queue depth. After all completions
are reaped, the example reports the total execution time and the corresponding
IOPS rate.

## Key features

- Choose how many I/O queues to create (`-q`).
- Control the per-command LBA increment (`-m`) and LBA span (`-l`).
- Optionally override the queue depth used for each qpair (`-Q`).
- Submit either read (default) or write (`-W`) commands.
- Display controller MQES, the queue layout, total runtime, and calculated IOPS.

## Building

```bash
meson setup build
ninja -C build examples/nvme/queue_depth_burst
```

## Example usage

Run four queues on the first local PCIe controller, advancing by 16 LBAs per
command while transferring eight blocks per command. The `-r` argument is
optional for PCIe, but shown here for completeness:

```bash
sudo ./build/examples/queue_depth_burst \
  -r "trtype:PCIe" \
  -q 4 \
  -m 16 \
  -l 8
```

Select an NVMe transport other than local PCIe by passing a transport ID:

```bash
sudo ./build/examples/queue_depth_burst -r "trtype:TCP adrfam:IPv4 traddr:192.168.100.8 trsvcid:4420" -q 8
```

Set the queue depth explicitly to 512 entries per qpair:

```bash
sudo ./build/examples/queue_depth_burst -Q 512
```
