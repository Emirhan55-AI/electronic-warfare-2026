#ifndef P0_DMA_UAPI_H
#define P0_DMA_UAPI_H

#include <linux/ioctl.h>
#include <linux/types.h>

#define P0_DMA_ABI_VERSION 2U
#define P0_DMA_RUNTIME_ABI_VERSION 3U
#define P0_DMA_INPUT_BYTES 8192U
#define P0_DMA_MAX_INPUT_BYTES 32768U
#define P0_DMA_OUTPUT_MINIMUM_BYTES 64U
#define P0_DMA_OUTPUT_CAPACITY_BYTES 54144U
#define P0_DMA_MAX_OUTPUT_CAPACITY_BYTES 131072U
#define P0_DMA_OUTPUT_ALIGNMENT_BYTES 8U

struct p0_dma_status {
    __u32 abi_version;
    __u32 input_bytes;
    __u32 output_capacity_bytes;
    __u32 output_bytes;
    __u32 input_dma_address;
    __u32 output_dma_address;
    __u32 mm2s_status;
    __u32 s2mm_status;
    __u32 mm2s_irq_status;
    __u32 s2mm_irq_status;
    __u32 input_loaded;
    __u32 output_valid;
    __u32 mm2s_completed;
    __u32 s2mm_completed;
    __u32 timed_out;
    __u32 dma_error;
};

_Static_assert(sizeof(struct p0_dma_status) == 64U, "P0 DMA status ABI drift");

#define P0_DMA_IOC_MAGIC 'P'
#define P0_DMA_IOC_RUN _IO(P0_DMA_IOC_MAGIC, 1)
#define P0_DMA_IOC_GET_STATUS _IOR(P0_DMA_IOC_MAGIC, 2, struct p0_dma_status)
#define P0_DMA_IOC_RESET _IO(P0_DMA_IOC_MAGIC, 3)

#define P0_DETECTION_CONFIG_ABI 1U
#define P0_DETECTION_CONTROL_ID 0x53540601U
struct p0_detection_config {
    __u32 abi_version;
    __u32 generation;
    __u64 alpha_q32;
    __u64 weak_alpha_q32;
};
_Static_assert(sizeof(struct p0_detection_config) == 24U, "Detection config ABI drift");
#define P0_DMA_IOC_GET_DETECTION_CONFIG _IOR(P0_DMA_IOC_MAGIC, 4, struct p0_detection_config)
#define P0_DMA_IOC_SET_DETECTION_CONFIG _IOWR(P0_DMA_IOC_MAGIC, 5, struct p0_detection_config)

#define P0_DETECTION_PROFILE_ABI 2U
#define P0_DETECTION_PROFILE_CONTROL_ID 0x53540602U
struct p0_detection_profile {
    __u32 abi_version;
    __u32 generation;
    __u32 fft_size;
    __u32 reserved;
    __u64 alpha_q32;
    __u64 weak_alpha_q32;
};
_Static_assert(sizeof(struct p0_detection_profile) == 32U,
               "Detection profile ABI drift");
#define P0_DMA_IOC_GET_DETECTION_PROFILE \
    _IOR(P0_DMA_IOC_MAGIC, 6, struct p0_detection_profile)
#define P0_DMA_IOC_SET_DETECTION_PROFILE \
    _IOWR(P0_DMA_IOC_MAGIC, 7, struct p0_detection_profile)

#endif
