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

## Automating stride sweeps

Use the helper script to sweep the LBA stride (`-m`) and generate an IOPS
trend. For example, run strides from 1 to 10,000 in steps of 100, saving both
plot and CSV:

```bash
python3 examples/nvme/queue_depth_burst/sweep_stride_iops.py \
  --binary ./build/examples/queue_depth_burst \
  --transport "trtype:PCIe" \
  --queue 1 \
  --lba-span 1 \
  --start 1 --stop 10000 --step 100 \
  --save stride_iops.png --csv stride_iops.csv
```
