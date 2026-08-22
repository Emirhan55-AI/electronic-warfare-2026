#ifndef P0_DMA_UAPI_H
#define P0_DMA_UAPI_H

#include <linux/ioctl.h>
#include <linux/types.h>

#define P0_DMA_ABI_VERSION 1U
#define P0_DMA_INPUT_BYTES 8192U
#define P0_DMA_OUTPUT_BYTES 32768U

struct p0_dma_status {
    __u32 abi_version;
    __u32 input_bytes;
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

#define P0_DMA_IOC_MAGIC 'P'
#define P0_DMA_IOC_RUN _IO(P0_DMA_IOC_MAGIC, 1)
#define P0_DMA_IOC_GET_STATUS _IOR(P0_DMA_IOC_MAGIC, 2, struct p0_dma_status)
#define P0_DMA_IOC_RESET _IO(P0_DMA_IOC_MAGIC, 3)

#endif
