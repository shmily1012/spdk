root@PAE-system:~/spdk# make
ninja: Entering directory `/root/spdk/dpdk/build-tmp'
ninja: no work to do.
  CC examples/nvme/wrr_burst_test/wrr_burst_test.o
In file included from wrr_burst_test.c:16:
../../../lib/nvme/nvme_pcie_internal.h:29:32: error: field ‘ctrlr’ has incomplete type
   29 |         struct spdk_nvme_ctrlr ctrlr;
      |                                ^~~~~
../../../lib/nvme/nvme_pcie_internal.h:113:47: error: field ‘group’ has incomplete type
  113 |         struct spdk_nvme_transport_poll_group group;
      |                                               ^~~~~
../../../lib/nvme/nvme_pcie_internal.h:175:32: error: field ‘qpair’ has incomplete type
  175 |         struct spdk_nvme_qpair qpair;
      |                                ^~~~~
../../../lib/nvme/nvme_pcie_internal.h: In function ‘nvme_pcie_qpair_update_mmio_required’:
../../../lib/nvme/nvme_pcie_internal.h:230:9: warning: implicit declaration of function ‘spdk_wmb’ [-Wimplicit-function-declaration]
  230 |         spdk_wmb();
      |         ^~~~~~~~
../../../lib/nvme/nvme_pcie_internal.h:239:9: warning: implicit declaration of function ‘spdk_mb’; did you mean ‘spdk_min’? [-Wimplicit-function-declaration]
  239 |         spdk_mb();
      |         ^~~~~~~
      |         spdk_min
../../../lib/nvme/nvme_pcie_internal.h: In function ‘nvme_pcie_qpair_ring_sq_doorbell’:
../../../lib/nvme/nvme_pcie_internal.h:252:64: error: invalid use of undefined type ‘struct spdk_nvme_qpair’
  252 |         struct nvme_pcie_ctrlr  *pctrlr = nvme_pcie_ctrlr(qpair->ctrlr);
      |                                                                ^~
../../../lib/nvme/nvme_pcie_internal.h:255:18: error: invalid use of undefined type ‘struct spdk_nvme_qpair’
  255 |         if (qpair->last_fuse == SPDK_NVME_IO_FLAGS_FUSE_FIRST) {
      |                  ^~
../../../lib/nvme/nvme_pcie_internal.h:260:13: warning: implicit declaration of function ‘spdk_unlikely’ [-Wimplicit-function-declaration]
  260 |         if (spdk_unlikely(pqpair->flags.has_shadow_doorbell)) {
      |             ^~~~~~~~~~~~~
../../../lib/nvme/nvme_pcie_internal.h:268:13: warning: implicit declaration of function ‘spdk_likely’ [-Wimplicit-function-declaration]
  268 |         if (spdk_likely(need_mmio)) {
      |             ^~~~~~~~~~~
../../../lib/nvme/nvme_pcie_internal.h:272:17: warning: implicit declaration of function ‘spdk_mmio_write_4’; did you mean ‘spdk_json_write_val’? [-Wimplicit-function-declaration]
  272 |                 spdk_mmio_write_4(pqpair->sq_tdbl, pqpair->sq_tail);
      |                 ^~~~~~~~~~~~~~~~~
      |                 spdk_json_write_val
../../../lib/nvme/nvme_pcie_internal.h: In function ‘nvme_pcie_qpair_ring_cq_doorbell’:
../../../lib/nvme/nvme_pcie_internal.h:281:64: error: invalid use of undefined type ‘struct spdk_nvme_qpair’
  281 |         struct nvme_pcie_ctrlr  *pctrlr = nvme_pcie_ctrlr(qpair->ctrlr);
      |                                                                ^~
wrr_burst_test.c: In function ‘parse_nonnegative_u32’:
wrr_burst_test.c:231:42: warning: multi-character character constant [-Wmultichar]
  231 |         if (endptr == NULL || *endptr != '\\0' || tmp > UINT32_MAX) {
      |                                          ^~~~~
wrr_burst_test.c:231:39: warning: comparison is always true due to limited range of data type [-Wtype-limits]
  231 |         if (endptr == NULL || *endptr != '\\0' || tmp > UINT32_MAX) {
      |                                       ^~
In file included from wrr_burst_test.c:16:
../../../lib/nvme/nvme_pcie_internal.h: In function ‘nvme_pcie_qpair’:
../../../lib/nvme/nvme_pcie_internal.h:209:1: warning: control reaches end of non-void function [-Wreturn-type]
  209 | }
      | ^
make[3]: *** [/root/spdk/mk/spdk.common.mk:540: wrr_burst_test.o] Error 1
make[2]: *** [/root/spdk/mk/spdk.subdirs.mk:16: wrr_burst_test] Error 2
make[1]: *** [/root/spdk/mk/spdk.subdirs.mk:16: nvme] Error 2
make: *** [/root/spdk/mk/spdk.subdirs.mk:16: examples] Error 2
root@PAE-system:~/spdk# 