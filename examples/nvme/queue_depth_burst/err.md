root@PAE-system:~/spdk# ./build/examples/queue_depth_burst -q 1 -m 64 -l 1
EAL: '-c <coremask>' option is deprecated, and will be removed in a future release
EAL:    Use '-l <corelist>' or '--lcores=<corelist>' option instead
[2025-09-29 21:34:01.395589] nvme.c:1039:spdk_nvme_trid_populate_transport: *ERROR*: no available transports
[2025-09-29 21:34:01.395640] nvme.c: 765:nvme_probe_internal: *ERROR*: NVMe trtype 0 () not available
[2025-09-29 21:34:01.395648] nvme.c: 883:spdk_nvme_probe_ext: *ERROR*: Create probe context failed
spdk_nvme_probe() failed (Operation not permitted)
root@PAE-system:~/spdk# 