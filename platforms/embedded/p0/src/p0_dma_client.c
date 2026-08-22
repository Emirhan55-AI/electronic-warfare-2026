#include <linux/completion.h>
#include <linux/dma-mapping.h>
#include <linux/fs.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/iopoll.h>
#include <linux/miscdevice.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/uaccess.h>

#include "p0_dma_uapi.h"

#define P0_MM2S_DMACR 0x00
#define P0_MM2S_DMASR 0x04
#define P0_MM2S_SA 0x18
#define P0_MM2S_LENGTH 0x28
#define P0_S2MM_DMACR 0x30
#define P0_S2MM_DMASR 0x34
#define P0_S2MM_DA 0x48
#define P0_S2MM_LENGTH 0x58

#define P0_DMACR_RS BIT(0)
#define P0_DMACR_RESET BIT(2)
#define P0_DMACR_IOC_IRQ_EN BIT(12)
#define P0_DMACR_ERR_IRQ_EN BIT(14)
#define P0_DMASR_HALTED BIT(0)
#define P0_DMASR_DMA_INT_ERR BIT(4)
#define P0_DMASR_DMA_SLV_ERR BIT(5)
#define P0_DMASR_DMA_DEC_ERR BIT(6)
#define P0_DMASR_SG_INT_ERR BIT(8)
#define P0_DMASR_SG_SLV_ERR BIT(9)
#define P0_DMASR_SG_DEC_ERR BIT(10)
#define P0_DMASR_IOC_IRQ BIT(12)
#define P0_DMASR_DLY_IRQ BIT(13)
#define P0_DMASR_ERR_IRQ BIT(14)

#define P0_DMASR_IRQ_MASK (P0_DMASR_IOC_IRQ | P0_DMASR_DLY_IRQ | P0_DMASR_ERR_IRQ)
#define P0_DMASR_ERROR_MASK                                                   \
    (P0_DMASR_DMA_INT_ERR | P0_DMASR_DMA_SLV_ERR | P0_DMASR_DMA_DEC_ERR |   \
     P0_DMASR_SG_INT_ERR | P0_DMASR_SG_SLV_ERR | P0_DMASR_SG_DEC_ERR)
#define P0_DMACR_RUN_IRQ                                                      \
    (P0_DMACR_RS | P0_DMACR_IOC_IRQ_EN | P0_DMACR_ERR_IRQ_EN)
#define P0_RESET_TIMEOUT_US 100000
#define P0_RUN_TIMEOUT_MS 5000

struct p0_dma_device {
    struct device *device;
    void __iomem *registers;
    void *input_cpu;
    dma_addr_t input_dma;
    void *output_cpu;
    dma_addr_t output_dma;
    struct completion mm2s_completion;
    struct completion s2mm_completion;
    struct mutex lock;
    struct miscdevice misc;
    struct p0_dma_status status;
};

static inline u32 p0_read(struct p0_dma_device *dma, u32 offset)
{
    return readl(dma->registers + offset);
}

static inline void p0_write(struct p0_dma_device *dma, u32 offset, u32 value)
{
    writel(value, dma->registers + offset);
}

static void p0_snapshot_status(struct p0_dma_device *dma)
{
    dma->status.mm2s_status = p0_read(dma, P0_MM2S_DMASR);
    dma->status.s2mm_status = p0_read(dma, P0_S2MM_DMASR);
}

static int p0_reset_locked(struct p0_dma_device *dma)
{
    u32 value;
    int result;

    p0_write(dma, P0_MM2S_DMACR, P0_DMACR_RESET);
    result = readl_poll_timeout(dma->registers + P0_MM2S_DMACR, value,
                                !(value & P0_DMACR_RESET), 10,
                                P0_RESET_TIMEOUT_US);
    if (result)
        return result;

    p0_write(dma, P0_MM2S_DMASR, P0_DMASR_IRQ_MASK);
    p0_write(dma, P0_S2MM_DMASR, P0_DMASR_IRQ_MASK);
    p0_snapshot_status(dma);
    return 0;
}

static void p0_stop_locked(struct p0_dma_device *dma)
{
    p0_write(dma, P0_MM2S_DMACR, 0);
    p0_write(dma, P0_S2MM_DMACR, 0);
    p0_snapshot_status(dma);
}

static irqreturn_t p0_mm2s_irq(int irq, void *data)
{
    struct p0_dma_device *dma = data;
    u32 status = p0_read(dma, P0_MM2S_DMASR);
    u32 pending = status & P0_DMASR_IRQ_MASK;

    if (!pending)
        return IRQ_NONE;
    p0_write(dma, P0_MM2S_DMASR, pending);
    dma->status.mm2s_irq_status = status;
    if ((status & P0_DMASR_ERROR_MASK) || (pending & P0_DMASR_ERR_IRQ))
        dma->status.dma_error = 1;
    if (pending & P0_DMASR_IOC_IRQ)
        dma->status.mm2s_completed = 1;
    complete(&dma->mm2s_completion);
    return IRQ_HANDLED;
}

static irqreturn_t p0_s2mm_irq(int irq, void *data)
{
    struct p0_dma_device *dma = data;
    u32 status = p0_read(dma, P0_S2MM_DMASR);
    u32 pending = status & P0_DMASR_IRQ_MASK;

    if (!pending)
        return IRQ_NONE;
    p0_write(dma, P0_S2MM_DMASR, pending);
    dma->status.s2mm_irq_status = status;
    if ((status & P0_DMASR_ERROR_MASK) || (pending & P0_DMASR_ERR_IRQ))
        dma->status.dma_error = 1;
    if (pending & P0_DMASR_IOC_IRQ)
        dma->status.s2mm_completed = 1;
    complete(&dma->s2mm_completion);
    return IRQ_HANDLED;
}

static int p0_start_channel(struct p0_dma_device *dma, u32 control,
                            u32 status)
{
    u32 value;

    p0_write(dma, control, P0_DMACR_RUN_IRQ);
    return readl_poll_timeout(dma->registers + status, value,
                              !(value & P0_DMASR_HALTED), 1,
                              P0_RESET_TIMEOUT_US);
}

static int p0_run_locked(struct p0_dma_device *dma)
{
    unsigned long mm2s_done;
    unsigned long s2mm_done;
    int result;

    if (!dma->status.input_loaded)
        return -ENODATA;

    dma->status.output_valid = 0;
    dma->status.mm2s_completed = 0;
    dma->status.s2mm_completed = 0;
    dma->status.timed_out = 0;
    dma->status.dma_error = 0;
    dma->status.mm2s_irq_status = 0;
    dma->status.s2mm_irq_status = 0;
    reinit_completion(&dma->mm2s_completion);
    reinit_completion(&dma->s2mm_completion);
    memset(dma->output_cpu, 0, P0_DMA_OUTPUT_BYTES);

    result = p0_reset_locked(dma);
    if (result)
        return result;

    dma_wmb();

    /* The receive channel is armed before MM2S can feed the DSP producer. */
    result = p0_start_channel(dma, P0_S2MM_DMACR, P0_S2MM_DMASR);
    if (result)
        goto fail;
    p0_write(dma, P0_S2MM_DA, lower_32_bits(dma->output_dma));
    p0_write(dma, P0_S2MM_LENGTH, P0_DMA_OUTPUT_BYTES);

    result = p0_start_channel(dma, P0_MM2S_DMACR, P0_MM2S_DMASR);
    if (result)
        goto fail;
    p0_write(dma, P0_MM2S_SA, lower_32_bits(dma->input_dma));
    p0_write(dma, P0_MM2S_LENGTH, P0_DMA_INPUT_BYTES);

    mm2s_done = wait_for_completion_timeout(
        &dma->mm2s_completion, msecs_to_jiffies(P0_RUN_TIMEOUT_MS));
    s2mm_done = wait_for_completion_timeout(
        &dma->s2mm_completion, msecs_to_jiffies(P0_RUN_TIMEOUT_MS));
    p0_snapshot_status(dma);

    if (!mm2s_done || !s2mm_done) {
        dma->status.timed_out = 1;
        result = -ETIMEDOUT;
        goto fail;
    }
    if (dma->status.dma_error || !dma->status.mm2s_completed ||
        !dma->status.s2mm_completed ||
        (dma->status.mm2s_status & P0_DMASR_ERROR_MASK) ||
        (dma->status.s2mm_status & P0_DMASR_ERROR_MASK)) {
        result = -EIO;
        goto fail;
    }

    dma_rmb();
    dma->status.output_valid = 1;
    return 0;

fail:
    p0_stop_locked(dma);
    return result;
}

static ssize_t p0_write_input(struct file *file, const char __user *buffer,
                              size_t count, loff_t *offset)
{
    struct p0_dma_device *dma = container_of(
        file->private_data, struct p0_dma_device, misc);
    int result = 0;

    (void)offset;
    if (count != P0_DMA_INPUT_BYTES)
        return -EINVAL;
    if (mutex_lock_interruptible(&dma->lock))
        return -ERESTARTSYS;
    if (copy_from_user(dma->input_cpu, buffer, count))
        result = -EFAULT;
    else {
        dma->status.input_loaded = 1;
        dma->status.output_valid = 0;
        result = count;
    }
    mutex_unlock(&dma->lock);
    return result;
}

static ssize_t p0_read_output(struct file *file, char __user *buffer,
                              size_t count, loff_t *offset)
{
    struct p0_dma_device *dma = container_of(
        file->private_data, struct p0_dma_device, misc);
    int result = 0;

    (void)offset;
    if (count != P0_DMA_OUTPUT_BYTES)
        return -EINVAL;
    if (mutex_lock_interruptible(&dma->lock))
        return -ERESTARTSYS;
    if (!dma->status.output_valid)
        result = -ENODATA;
    else if (copy_to_user(buffer, dma->output_cpu, count))
        result = -EFAULT;
    else
        result = count;
    mutex_unlock(&dma->lock);
    return result;
}

static long p0_ioctl(struct file *file, unsigned int command,
                     unsigned long argument)
{
    struct p0_dma_device *dma = container_of(
        file->private_data, struct p0_dma_device, misc);
    int result;

    if (_IOC_TYPE(command) != P0_DMA_IOC_MAGIC)
        return -ENOTTY;
    if (mutex_lock_interruptible(&dma->lock))
        return -ERESTARTSYS;

    switch (command) {
    case P0_DMA_IOC_RUN:
        result = p0_run_locked(dma);
        break;
    case P0_DMA_IOC_GET_STATUS:
        p0_snapshot_status(dma);
        result = copy_to_user((void __user *)argument, &dma->status,
                              sizeof(dma->status)) ? -EFAULT : 0;
        break;
    case P0_DMA_IOC_RESET:
        result = p0_reset_locked(dma);
        if (!result) {
            dma->status.input_loaded = 0;
            dma->status.output_valid = 0;
        }
        break;
    default:
        result = -ENOTTY;
        break;
    }

    mutex_unlock(&dma->lock);
    return result;
}

static const struct file_operations p0_file_operations = {
    .owner = THIS_MODULE,
    .read = p0_read_output,
    .write = p0_write_input,
    .unlocked_ioctl = p0_ioctl,
};

static int p0_probe(struct platform_device *platform)
{
    struct p0_dma_device *dma;
    int mm2s_irq;
    int s2mm_irq;
    int result;

    dma = devm_kzalloc(&platform->dev, sizeof(*dma), GFP_KERNEL);
    if (!dma)
        return -ENOMEM;
    dma->device = &platform->dev;
    dma->registers = devm_platform_ioremap_resource(platform, 0);
    if (IS_ERR(dma->registers))
        return PTR_ERR(dma->registers);

    result = dma_set_mask_and_coherent(&platform->dev, DMA_BIT_MASK(32));
    if (result)
        return result;
    dma->input_cpu = dmam_alloc_coherent(&platform->dev, P0_DMA_INPUT_BYTES,
                                         &dma->input_dma, GFP_KERNEL);
    dma->output_cpu = dmam_alloc_coherent(&platform->dev, P0_DMA_OUTPUT_BYTES,
                                          &dma->output_dma, GFP_KERNEL);
    if (!dma->input_cpu || !dma->output_cpu)
        return -ENOMEM;
    if (upper_32_bits(dma->input_dma) || upper_32_bits(dma->output_dma) ||
        (dma->input_dma & 0x7) || (dma->output_dma & 0x7))
        return -EINVAL;

    mutex_init(&dma->lock);
    init_completion(&dma->mm2s_completion);
    init_completion(&dma->s2mm_completion);
    dma->status.abi_version = P0_DMA_ABI_VERSION;
    dma->status.input_bytes = P0_DMA_INPUT_BYTES;
    dma->status.output_bytes = P0_DMA_OUTPUT_BYTES;
    dma->status.input_dma_address = lower_32_bits(dma->input_dma);
    dma->status.output_dma_address = lower_32_bits(dma->output_dma);

    mm2s_irq = platform_get_irq_byname(platform, "mm2s_introut");
    if (mm2s_irq < 0)
        return mm2s_irq;
    s2mm_irq = platform_get_irq_byname(platform, "s2mm_introut");
    if (s2mm_irq < 0)
        return s2mm_irq;
    result = devm_request_irq(&platform->dev, mm2s_irq, p0_mm2s_irq, 0,
                              "p0-dma-mm2s", dma);
    if (result)
        return result;
    result = devm_request_irq(&platform->dev, s2mm_irq, p0_s2mm_irq, 0,
                              "p0-dma-s2mm", dma);
    if (result)
        return result;

    dma->misc.minor = MISC_DYNAMIC_MINOR;
    dma->misc.name = "p0-dma";
    dma->misc.fops = &p0_file_operations;
    dma->misc.parent = &platform->dev;
    dma->misc.mode = 0600;
    result = misc_register(&dma->misc);
    if (result)
        return result;
    platform_set_drvdata(platform, dma);

    result = p0_reset_locked(dma);
    if (result) {
        misc_deregister(&dma->misc);
        return result;
    }
    dev_info(&platform->dev,
             "P0 DMA ready: input=%pad/8192 output=%pad/32768\n",
             &dma->input_dma, &dma->output_dma);
    return 0;
}

static void p0_remove(struct platform_device *platform)
{
    struct p0_dma_device *dma = platform_get_drvdata(platform);

    mutex_lock(&dma->lock);
    p0_reset_locked(dma);
    mutex_unlock(&dma->lock);
    misc_deregister(&dma->misc);
}

static const struct of_device_id p0_of_match[] = {
    { .compatible = "teknofest,p0-axi-dma-1.0" },
    { }
};
MODULE_DEVICE_TABLE(of, p0_of_match);

static struct platform_driver p0_driver = {
    .probe = p0_probe,
    .remove = p0_remove,
    .driver = {
        .name = "p0-dma-client",
        .of_match_table = p0_of_match,
    },
};
module_platform_driver(p0_driver);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("TEKNOFEST P0");
MODULE_DESCRIPTION("P0 coherent direct-mode AXI DMA client");
