/*   SPDX-License-Identifier: BSD-3-Clause */

#include "spdk/stdinc.h"

#include "spdk/env.h"
#include "spdk/log.h"
#include "spdk/nvme.h"
#include "spdk/string.h"
#include "spdk/vmd.h"

#include <getopt.h>

struct ctrlr_entry {
	struct spdk_nvme_ctrlr *ctrlr;
	TAILQ_ENTRY(ctrlr_entry) link;
	char name[128];
};

struct ns_entry {
	struct spdk_nvme_ctrlr *ctrlr;
	struct spdk_nvme_ns *ns;
	TAILQ_ENTRY(ns_entry) link;
};

struct io_task;

struct qpair_ctx {
	struct spdk_nvme_qpair *qpair;
	struct ns_entry *ns_entry;
	struct io_task *tasks;
	void *buffer_pool;
	size_t payload_size;
	uint32_t queue_depth;
	uint64_t base_lba;
	uint32_t outstanding;
};

struct io_task {
	struct qpair_ctx *owner;
	void *buffer;
	uint64_t lba;
	uint64_t submit_tick;
	uint64_t completion_tick;
	bool success;
};

struct app_config {
	uint32_t queue_count;
	uint32_t lba_count;
	uint64_t start_lba;
	uint32_t lba_stride;
	uint32_t queue_depth;
	bool write;
	bool enable_vmd;
};

struct app_stats {
	uint64_t submitted;
	uint64_t completed;
	uint64_t errors;
	uint64_t first_doorbell_tick;
	uint64_t last_completion_tick;
};

static struct app_config g_cfg = {
	.queue_count = 1,
	.lba_count = 8,
	.start_lba = 0,
	.lba_stride = 8,
	.queue_depth = 0,
	.write = false,
	.enable_vmd = false,
};

static struct app_stats g_stats = {};
static bool g_stride_overridden = false;

static TAILQ_HEAD(, ctrlr_entry) g_controllers = TAILQ_HEAD_INITIALIZER(g_controllers);
static TAILQ_HEAD(, ns_entry) g_namespaces = TAILQ_HEAD_INITIALIZER(g_namespaces);
static struct spdk_nvme_transport_id g_trid = {};

static void
cleanup(void)
{
	struct ns_entry *ns_entry, *tmp_ns_entry;
	struct ctrlr_entry *ctrlr_entry, *tmp_ctrlr_entry;
	struct spdk_nvme_detach_ctx *detach_ctx = NULL;

	TAILQ_FOREACH_SAFE(ns_entry, &g_namespaces, link, tmp_ns_entry) {
		TAILQ_REMOVE(&g_namespaces, ns_entry, link);
		free(ns_entry);
	}

	TAILQ_FOREACH_SAFE(ctrlr_entry, &g_controllers, link, tmp_ctrlr_entry) {
		TAILQ_REMOVE(&g_controllers, ctrlr_entry, link);
		if (spdk_nvme_detach_async(ctrlr_entry->ctrlr, &detach_ctx)) {
			SPDK_ERRLOG("Failed to detach controller %s\n", ctrlr_entry->name);
		}
		free(ctrlr_entry);
	}

	if (detach_ctx != NULL) {
		spdk_nvme_detach_poll(detach_ctx);
	}
}

static void
usage(const char *program)
{
	printf("Usage: %s [options]\n", program);
	printf("\n");
	printf("Options:\n");
	printf("  -h, --help\t\tShow this message.\n");
	printf("  -r <trid>\t\tNVMe transport ID (default: local PCIe).\n");
	printf("  -d <MB>\t\tDPDK hugepage memory size.\n");
	printf("  -i <id>\t\tShared memory group ID.\n");
	printf("  -g\t\t\tUse a single file descriptor for hugepages.\n");
	printf("  -q <num>\t\tI/O queue pairs to allocate (default %u).\n", g_cfg.queue_count);
	printf("  -Q <depth>\tOptional queue depth override per qpair.\n");
	printf("  -m <stride>\tLBA increment between commands on a queue (default %u).\n", g_cfg.lba_stride);
	printf("  -l <lbas>\tLogical blocks per command (default %u).\n", g_cfg.lba_count);
	printf("  -s <lba>\t\tStarting LBA (default %" PRIu64 ").\n", g_cfg.start_lba);
	printf("  -W, --write\t\tIssue write commands instead of reads.\n");
	printf("      --vmd\t\tEnable VMD enumeration.\n");
	printf("\nExample:\n");
	printf("  %s -q 4 -m 16 -l 8\n", program);
}

static int
parse_positive_u32(const char *arg, uint32_t *value)
{
	char *endptr = NULL;
	uint64_t tmp;

	tmp = strtoull(arg, &endptr, 10);
	if (endptr == NULL || *endptr != '\0' || tmp == 0 || tmp > UINT32_MAX) {
		return -EINVAL;
	}

	*value = (uint32_t)tmp;
	return 0;
}

static int
parse_non_negative_u64(const char *arg, uint64_t *value)
{
	char *endptr = NULL;
	uint64_t tmp;

	tmp = strtoull(arg, &endptr, 10);
	if (endptr == NULL || *endptr != '\0') {
		return -EINVAL;
	}

	*value = tmp;
	return 0;
}

static void
register_ns(struct spdk_nvme_ctrlr *ctrlr, struct spdk_nvme_ns *ns)
{
	struct ns_entry *entry;

	if (!spdk_nvme_ns_is_active(ns)) {
		return;
	}

	entry = calloc(1, sizeof(*entry));
	if (entry == NULL) {
		perror("ns_entry");
		exit(1);
	}

	entry->ctrlr = ctrlr;
	entry->ns = ns;
	TAILQ_INSERT_TAIL(&g_namespaces, entry, link);

	printf("  Namespace ID: %d size: %juGB\n", spdk_nvme_ns_get_id(ns),
	       spdk_nvme_ns_get_size(ns) / 1000000000);
}

static bool
probe_cb(void *cb_ctx, const struct spdk_nvme_transport_id *trid, struct spdk_nvme_ctrlr_opts *opts)
{
	printf("Probing NVMe controller at %s\n", trid->traddr);
	(void)cb_ctx;
	(void)opts;
	return true;
}

static void
attach_cb(void *cb_ctx, const struct spdk_nvme_transport_id *trid, struct spdk_nvme_ctrlr *ctrlr,
	   const struct spdk_nvme_ctrlr_opts *opts)
{
	struct ctrlr_entry *entry;
	const struct spdk_nvme_ctrlr_data *cdata;
	int nsid;

	(void)cb_ctx;
	(void)opts;

	entry = calloc(1, sizeof(*entry));
	if (entry == NULL) {
		perror("ctrlr_entry");
		exit(1);
	}

	cdata = spdk_nvme_ctrlr_get_data(ctrlr);
	snprintf(entry->name, sizeof(entry->name), "%-20.20s (%-20.20s)", cdata->mn, cdata->sn);

	entry->ctrlr = ctrlr;
	TAILQ_INSERT_TAIL(&g_controllers, entry, link);

	printf("Attached to %s\n", trid->traddr);

	for (nsid = spdk_nvme_ctrlr_get_first_active_ns(ctrlr); nsid != 0;
	     nsid = spdk_nvme_ctrlr_get_next_active_ns(ctrlr, nsid)) {
		register_ns(ctrlr, spdk_nvme_ctrlr_get_ns(ctrlr, nsid));
	}
}

static void
io_complete(void *arg, const struct spdk_nvme_cpl *cpl)
{
	struct io_task *task = arg;
	struct qpair_ctx *ctx = task->owner;

	task->completion_tick = spdk_get_ticks();
	task->success = !spdk_nvme_cpl_is_error(cpl);

	ctx->outstanding--;
	g_stats.completed++;
	g_stats.last_completion_tick = task->completion_tick;

	if (!task->success) {
		g_stats.errors++;
		spdk_nvme_qpair_print_completion(ctx->qpair, (struct spdk_nvme_cpl *)cpl);
	}
}

static int
prime_queue(struct qpair_ctx *ctx, uint32_t lba_count, uint32_t stride, bool write)
{
	struct spdk_nvme_ns *ns = ctx->ns_entry->ns;
	uint32_t i;
	int rc;

	for (i = 0; i < ctx->queue_depth; ++i) {
		struct io_task *task = &ctx->tasks[i];
		uint64_t lba = ctx->base_lba + (uint64_t)i * stride;

		task->lba = lba;
		task->submit_tick = spdk_get_ticks();

		if (write) {
			rc = spdk_nvme_ns_cmd_write(ns, ctx->qpair, task->buffer, lba, lba_count,
					     io_complete, task, 0);
		} else {
			rc = spdk_nvme_ns_cmd_read(ns, ctx->qpair, task->buffer, lba, lba_count,
					    io_complete, task, 0);
		}

		if (rc != 0) {
			SPDK_ERRLOG("Failed to submit command on qpair %u (rc=%d)\n",
				spdk_nvme_qpair_get_id(ctx->qpair), rc);
			return rc;
		}

		ctx->outstanding++;
		g_stats.submitted++;
	}

	return 0;
}

static void
flush_qpair(struct qpair_ctx *ctx)
{
	(void)spdk_nvme_qpair_process_completions(ctx->qpair, 0);
}

static int
run_queue_depth_burst(struct ns_entry *target)
{
	struct qpair_ctx *qpairs;
	uint32_t i;
	int rc = 0;
	uint64_t ns_size;
	uint32_t block_size;
	uint64_t commands_expected = 0;
	uint64_t max_lba_required = 0;
	union spdk_nvme_cap_register cap;

	block_size = spdk_nvme_ns_get_sector_size(target->ns);
	ns_size = spdk_nvme_ns_get_num_sectors(target->ns);
	cap = spdk_nvme_ctrlr_get_regs_cap(target->ctrlr);

	printf("\nNamespace %d information:\n", spdk_nvme_ns_get_id(target->ns));
	printf("  Sector size          : %u bytes\n", block_size);
	printf("  Total sectors        : %" PRIu64 "\n", ns_size);
	printf("  Controller MQES      : %u entries\n", cap.bits.mqes + 1);

	qpairs = calloc(g_cfg.queue_count, sizeof(*qpairs));
	if (qpairs == NULL) {
		return -ENOMEM;
	}

	for (i = 0; i < g_cfg.queue_count; ++i) {
		struct qpair_ctx *ctx = &qpairs[i];
		struct spdk_nvme_io_qpair_opts opts;

		spdk_nvme_ctrlr_get_default_io_qpair_opts(target->ctrlr, &opts, sizeof(opts));

		uint32_t max_entries = cap.bits.mqes + 1;
		uint32_t desired_depth = (g_cfg.queue_depth != 0) ? g_cfg.queue_depth : opts.io_queue_size;
		if (desired_depth > max_entries) {
			desired_depth = max_entries;
		}

		uint32_t queue_entries = opts.io_queue_size;
		if (queue_entries < desired_depth) {
			queue_entries = desired_depth;
		}
		if (queue_entries == desired_depth && queue_entries < max_entries) {
			/* Leave one spare slot so the tail doorbell reflects the burst size. */
			queue_entries++;
		}
		if (queue_entries > max_entries) {
			queue_entries = max_entries;
			if (desired_depth > queue_entries) {
				desired_depth = queue_entries;
			}
		}

		opts.io_queue_size = queue_entries;
		if (opts.io_queue_requests < opts.io_queue_size) {
			opts.io_queue_requests = opts.io_queue_size;
		}
		opts.delay_cmd_submit = true;

		ctx->payload_size = (size_t)g_cfg.lba_count * block_size;
		ctx->buffer_pool = spdk_zmalloc(ctx->payload_size * opts.io_queue_size,
					   block_size, NULL, SPDK_ENV_NUMA_ID_ANY, SPDK_MALLOC_DMA);
		if (ctx->buffer_pool == NULL) {
			SPDK_ERRLOG("Unable to allocate I/O buffer for qpair %u\n", i);
			rc = -ENOMEM;
			goto cleanup;
		}

		ctx->tasks = calloc(opts.io_queue_size, sizeof(*ctx->tasks));
		if (ctx->tasks == NULL) {
			SPDK_ERRLOG("Unable to allocate task array for qpair %u\n", i);
			rc = -ENOMEM;
			goto cleanup;
		}

		ctx->qpair = spdk_nvme_ctrlr_alloc_io_qpair(target->ctrlr, &opts, sizeof(opts));
		if (ctx->qpair == NULL) {
			SPDK_ERRLOG("Failed to allocate I/O qpair %u\n", i);
			rc = -ENOMEM;
			goto cleanup;
		}

		ctx->ns_entry = target;
		ctx->queue_depth = desired_depth;
		ctx->base_lba = g_cfg.start_lba + (uint64_t)i;
		ctx->outstanding = 0;

		for (uint32_t j = 0; j < ctx->queue_depth; ++j) {
			ctx->tasks[j].owner = ctx;
			ctx->tasks[j].buffer = (uint8_t *)ctx->buffer_pool + (size_t)j * ctx->payload_size;
		}

		if (ctx->queue_depth == 0) {
			SPDK_ERRLOG("Queue depth cannot be zero.\n");
			rc = -EINVAL;
			goto cleanup;
		}

		commands_expected += ctx->queue_depth;

		if (ctx->queue_depth > 0) {
			uint64_t last_lba = ctx->base_lba + (uint64_t)(ctx->queue_depth - 1) * g_cfg.lba_stride + g_cfg.lba_count;
			if (last_lba > max_lba_required) {
				max_lba_required = last_lba;
			}
		}

		printf("  Qpair %u burst %u (SQ entries %u) base LBA %" PRIu64 "\n",
		       i, ctx->queue_depth, queue_entries, ctx->base_lba);
	}

	if (max_lba_required > ns_size) {
		SPDK_ERRLOG("Requested range exceeds namespace capacity (need %" PRIu64 ", have %" PRIu64 ").\n",
			    max_lba_required, ns_size);
		rc = -ERANGE;
		goto cleanup;
	}

	printf("\nBurst parameters:\n");
	printf("  Queue pairs          : %u\n", g_cfg.queue_count);
	printf("  Commands per queue   : %u\n", (g_cfg.queue_count > 0) ? qpairs[0].queue_depth : 0);
	printf("  LBA stride           : %u\n", g_cfg.lba_stride);
	printf("  LBAs per command     : %u\n", g_cfg.lba_count);
	printf("  Mode                 : %s\n", g_cfg.write ? "write" : "read");

	g_stats.submitted = 0;
	g_stats.completed = 0;
	g_stats.errors = 0;
	g_stats.first_doorbell_tick = 0;
	g_stats.last_completion_tick = 0;

	for (i = 0; i < g_cfg.queue_count; ++i) {
		rc = prime_queue(&qpairs[i], g_cfg.lba_count, g_cfg.lba_stride, g_cfg.write);
		if (rc != 0) {
			goto cleanup;
		}
	}

	g_stats.first_doorbell_tick = spdk_get_ticks();

	for (i = 0; i < g_cfg.queue_count; ++i) {
		flush_qpair(&qpairs[i]);
	}

	while (g_stats.completed < commands_expected) {
		for (i = 0; i < g_cfg.queue_count; ++i) {
			int32_t completions = spdk_nvme_qpair_process_completions(qpairs[i].qpair, 0);
			if (completions < 0) {
				SPDK_ERRLOG("Completion polling failed on qpair %u (rc=%d)\n", i, completions);
				rc = completions;
				goto cleanup;
			}
		}
	}

	if (g_stats.last_completion_tick <= g_stats.first_doorbell_tick) {
		SPDK_ERRLOG("Invalid timing data collected.\n");
		rc = -EINVAL;
		goto cleanup;
	}

	{
		double elapsed_ticks = (double)(g_stats.last_completion_tick - g_stats.first_doorbell_tick);
		double seconds = elapsed_ticks / (double)spdk_get_ticks_hz();
		double iops = (seconds > 0.0) ? (commands_expected / seconds) : 0.0;

		printf("\nResults:\n");
		printf("  Commands completed   : %" PRIu64 "\n", g_stats.completed);
		printf("  Errors               : %" PRIu64 "\n", g_stats.errors);
		printf("  Elapsed time         : %.6f s\n", seconds);
		printf("  Simulated IOPS       : %.2f\n", iops);
	}

cleanup:
	for (i = 0; i < g_cfg.queue_count; ++i) {
		struct qpair_ctx *ctx = &qpairs[i];

		if (ctx->qpair != NULL) {
			spdk_nvme_ctrlr_free_io_qpair(ctx->qpair);
		}
		if (ctx->buffer_pool != NULL) {
			spdk_free(ctx->buffer_pool);
		}
		free(ctx->tasks);
	}

	free(qpairs);

	return rc;
}

static int
parse_args(int argc, char **argv, struct spdk_env_opts *env_opts)
{
	int opt, rc;
	int option_index;
	uint32_t u32;
	uint64_t u64;

	static const struct option long_options[] = {
		{ "help", no_argument, NULL, 'h' },
		{ "write", no_argument, NULL, 'W' },
		{ "vmd", no_argument, NULL, 0x100 },
		{ NULL, 0, NULL, 0 }
	};

	snprintf(g_trid.subnqn, sizeof(g_trid.subnqn), "%s", SPDK_NVMF_DISCOVERY_NQN);

	if (g_trid.trtype == SPDK_NVME_TRANSPORT_CUSTOM) {
		if (spdk_nvme_transport_id_populate_trstring(&g_trid, "PCIe") != 0) {
			fprintf(stderr, "Failed to set default transport type.\n");
			return -EINVAL;
		}
	}

	while ((opt = getopt_long(argc, argv, "hd:gi:r:q:Q:m:l:s:W", long_options, &option_index)) != -1) {
		switch (opt) {
		case 'h':
			usage(argv[0]);
			return 1;
		case 'd':
			rc = parse_positive_u32(optarg, &u32);
			if (rc != 0) {
				fprintf(stderr, "Invalid memory size '%s'\n", optarg);
				return rc;
			}
			env_opts->mem_size = u32;
			break;
		case 'g':
			env_opts->hugepage_single_segments = true;
			break;
		case 'i':
			rc = parse_positive_u32(optarg, &u32);
			if (rc != 0) {
				fprintf(stderr, "Invalid shared memory ID '%s'\n", optarg);
				return rc;
			}
			env_opts->shm_id = u32;
			break;
		case 'r':
			if (spdk_nvme_transport_id_parse(&g_trid, optarg) != 0) {
				fprintf(stderr, "Failed to parse transport ID '%s'\n", optarg);
				return -EINVAL;
			}
			break;
		case 'q':
			rc = parse_positive_u32(optarg, &u32);
			if (rc != 0 || u32 > 256U) {
				fprintf(stderr, "Invalid queue count '%s'\n", optarg);
				return -EINVAL;
			}
			g_cfg.queue_count = u32;
			break;
		case 'Q':
			rc = parse_positive_u32(optarg, &u32);
			if (rc != 0) {
				fprintf(stderr, "Invalid queue depth '%s'\n", optarg);
				return -EINVAL;
			}
			g_cfg.queue_depth = u32;
			break;
	case 'm':
		rc = parse_positive_u32(optarg, &u32);
		if (rc != 0) {
			fprintf(stderr, "Invalid LBA stride '%s'\n", optarg);
			return -EINVAL;
		}
		g_cfg.lba_stride = u32;
		g_stride_overridden = true;
		break;
		case 'l':
			rc = parse_positive_u32(optarg, &u32);
			if (rc != 0) {
				fprintf(stderr, "Invalid LBA count '%s'\n", optarg);
				return -EINVAL;
			}
			g_cfg.lba_count = u32;
			if (!g_stride_overridden) {
				g_cfg.lba_stride = u32;
			}
			break;
		case 's':
			rc = parse_non_negative_u64(optarg, &u64);
			if (rc != 0) {
				fprintf(stderr, "Invalid start LBA '%s'\n", optarg);
				return rc;
			}
			g_cfg.start_lba = u64;
			break;
		case 'W':
			g_cfg.write = true;
			break;
		case 0x100:
			g_cfg.enable_vmd = true;
			break;
		default:
			usage(argv[0]);
			return -EINVAL;
		}
	}

	if (g_cfg.lba_stride == 0) {
		g_cfg.lba_stride = g_cfg.lba_count;
	}

	return 0;
}

int
main(int argc, char **argv)
{
	int rc;
	struct spdk_env_opts opts;
	struct ns_entry *ns_entry;

	spdk_env_opts_init(&opts);
	opts.name = "queue_depth_burst";
	opts.shm_id = -1;

	rc = parse_args(argc, argv, &opts);
	if (rc != 0) {
		if (rc > 0) {
			return EXIT_SUCCESS;
		}
		return EXIT_FAILURE;
	}

	if (g_trid.trtype == SPDK_NVME_TRANSPORT_CUSTOM) {
		if (spdk_nvme_transport_id_populate_trstring(&g_trid, "PCIe") != 0) {
			fprintf(stderr, "Unsupported transport requested.\n");
			return EXIT_FAILURE;
		}
	}

	if (spdk_env_init(&opts) != 0) {
		fprintf(stderr, "Unable to initialize SPDK env\n");
		return EXIT_FAILURE;
	}

	if (g_cfg.enable_vmd) {
		if (spdk_vmd_init()) {
			fprintf(stderr, "VMD init failed\n");
			rc = EXIT_FAILURE;
			goto out;
		}
	}

	rc = spdk_nvme_probe(&g_trid, NULL, probe_cb, attach_cb, NULL);
	if (rc != 0) {
		fprintf(stderr, "spdk_nvme_probe() failed (%s)\n", spdk_strerror(-rc));
		rc = EXIT_FAILURE;
		goto out_vmd;
	}

	if (TAILQ_EMPTY(&g_namespaces)) {
		fprintf(stderr, "No active namespaces found.\n");
		rc = EXIT_FAILURE;
		goto out_vmd;
	}

	ns_entry = TAILQ_FIRST(&g_namespaces);

	rc = run_queue_depth_burst(ns_entry);
	if (rc != 0) {
		fprintf(stderr, "Test failed (%s)\n", spdk_strerror(-rc));
	}

out_vmd:
	if (g_cfg.enable_vmd) {
		spdk_vmd_fini();
	}

out:
	cleanup();
	spdk_env_fini();

	return (rc == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
