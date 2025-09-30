root@PAE-system:~/spdk# ./build/examples/queue_depth_burst   -r "trtype:PCIe"   -q 1   -m 100   -l 1
EAL: '-c <coremask>' option is deprecated, and will be removed in a future release
EAL:    Use '-l <corelist>' or '--lcores=<corelist>' option instead
Probing NVMe controller at 0000:01:00.0
Attached to 0000:01:00.0
  Namespace ID: 1 size: 3840GB

Namespace 1 information:
  Sector size          : 512 bytes
  Total sectors        : 7501476528
  Controller MQES      : 16384 entries
  Qpair 0 depth 256 base LBA 0

Burst parameters:
  Queue pairs          : 1
  Commands per queue   : 256
  LBA stride           : 100
  LBAs per command     : 1
  Mode                 : read

Results:
  Commands completed   : 256
  Errors               : 0
  Elapsed time         : 0.001120 s
  Simulated IOPS       : 228552.80
Segmentation fault (core dumped)
root@PAE-system:~/spdk# 