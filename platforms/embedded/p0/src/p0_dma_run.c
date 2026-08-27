#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "p0_dma_runtime.h"
#include "p0_dma_uapi.h"

static int read_exact_file(const char *path, uint8_t *buffer, size_t size)
{
    FILE *file = fopen(path, "rb");
    int extra;

    if (!file)
        return -1;
    if (fread(buffer, 1, size, file) != size) {
        fclose(file);
        errno = EINVAL;
        return -1;
    }
    extra = fgetc(file);
    fclose(file);
    if (extra != EOF) {
        errno = EFBIG;
        return -1;
    }
    return 0;
}

static int write_exact_file(const char *path, const uint8_t *buffer, size_t size)
{
    FILE *file = fopen(path, "wb");

    if (!file)
        return -1;
    if (fwrite(buffer, 1, size, file) != size || fclose(file) != 0)
        return -1;
    return 0;
}

static void print_status(const struct p0_dma_status *status)
{
    printf("ABI_VERSION=%u\n", status->abi_version);
    printf("INPUT_BYTES=%u\n", status->input_bytes);
    printf("OUTPUT_BYTES=%u\n", status->output_bytes);
    printf("INPUT_DMA=0x%08x\n", status->input_dma_address);
    printf("OUTPUT_DMA=0x%08x\n", status->output_dma_address);
    printf("MM2S_DMASR=0x%08x\n", status->mm2s_status);
    printf("S2MM_DMASR=0x%08x\n", status->s2mm_status);
    printf("MM2S_IRQ_STATUS=0x%08x\n", status->mm2s_irq_status);
    printf("S2MM_IRQ_STATUS=0x%08x\n", status->s2mm_irq_status);
    printf("MM2S_COMPLETE=%u\n", status->mm2s_completed);
    printf("S2MM_COMPLETE=%u\n", status->s2mm_completed);
    printf("TIMEOUT=%u\n", status->timed_out);
    printf("DMA_ERROR=%u\n", status->dma_error);
}

int main(int argc, char **argv)
{
    struct p0_dma_status status;
    uint8_t *input;
    uint8_t *output;
    p0_dma_runtime_t dma = {-1};
    int result = EXIT_FAILURE;

    if (argc != 3) {
        fprintf(stderr, "Kullanım: %s GIRIS_CI8 CIKIS_U64\n", argv[0]);
        return EXIT_FAILURE;
    }
    input = malloc(P0_DMA_INPUT_BYTES);
    output = malloc(P0_DMA_OUTPUT_BYTES);
    if (!input || !output) {
        fprintf(stderr, "Bellek ayrılamadı.\n");
        goto done;
    }
    if (read_exact_file(argv[1], input, P0_DMA_INPUT_BYTES) != 0) {
        fprintf(stderr, "Giriş okunamadı: %s\n", strerror(errno));
        goto done;
    }
    if (p0_dma_runtime_open(&dma, "/dev/p0-dma") != 0) {
        fprintf(stderr, "/dev/p0-dma açılamadı: %s\n", strerror(errno));
        goto done;
    }
    if (p0_dma_runtime_run(&dma, input, P0_DMA_INPUT_BYTES, output, P0_DMA_OUTPUT_BYTES,
                           &status) != 0) {
        print_status(&status);
        fprintf(stderr, "DMA çalıştırılamadı: %s\n", strerror(errno));
        goto close_device;
    }
    print_status(&status);
    if (write_exact_file(argv[2], output, P0_DMA_OUTPUT_BYTES) != 0) {
        fprintf(stderr, "Çıkış yazılamadı: %s\n", strerror(errno));
        goto close_device;
    }
    puts("P0_DMA_RESULT=PASS");
    result = EXIT_SUCCESS;

close_device:
    p0_dma_runtime_close(&dma);
done:
    free(output);
    free(input);
    return result;
}
