#include "p0_dma_runtime.h"
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static int mode;
static int calls;
int __wrap_ioctl(int fd, unsigned long request, ...);
int __wrap_ioctl(int fd, unsigned long request, ...)
{
    va_list args;
    void *argument;
    assert(fd == 42);
    va_start(args, request);
    argument = va_arg(args, void *);
    va_end(args);
    ++calls;
    if (mode == 1) { errno = EOPNOTSUPP; return -1; }
    if (mode == 2) { errno = ESTALE; return -1; }
    if (request == P0_DMA_IOC_GET_DETECTION_PROFILE ||
        request == P0_DMA_IOC_SET_DETECTION_PROFILE) {
        struct p0_detection_profile *profile = argument;
        if (request == P0_DMA_IOC_GET_DETECTION_PROFILE) {
            memset(profile, 0, sizeof(*profile));
            profile->abi_version = P0_DETECTION_PROFILE_ABI;
            profile->generation = 9;
            profile->fft_size = 8192;
            profile->alpha_q32 = UINT64_C(36851433755);
            profile->weak_alpha_q32 = UINT64_C(17098572778);
        } else {
            ++profile->generation;
        }
        if (mode == 3) profile->abi_version = 0;
        if (mode == 4) ++profile->alpha_q32;
        if (mode == 5) ++profile->generation;
        return 0;
    }
    {
    struct p0_detection_config *config = argument;
    if (request == P0_DMA_IOC_GET_DETECTION_CONFIG) {
        memset(config, 0, sizeof(*config));
        config->abi_version = P0_DETECTION_CONFIG_ABI;
        config->generation = 7;
        config->alpha_q32 = UINT64_C(36851433755);
        config->weak_alpha_q32 = UINT64_C(17098572778);
    } else {
        assert(request == P0_DMA_IOC_SET_DETECTION_CONFIG);
        ++config->generation;
    }
    if (mode == 3) config->abi_version = 0;
    if (mode == 4) ++config->alpha_q32;
    if (mode == 5) ++config->generation;
    }
    return 0;
}

int main(void)
{
    p0_dma_runtime_t runtime = {42};
    struct p0_detection_config config, before;
    struct p0_detection_profile profile, profile_before;
    int previous_calls;
    assert(p0_dma_runtime_get_detection_config(&runtime, &config) == 0);
    assert(config.generation == 7 && config.alpha_q32 == UINT64_C(36851433755));
    assert(p0_dma_runtime_set_detection_config(&runtime, &config) == 0);
    assert(config.generation == 8);
    config.generation = UINT32_MAX;
    assert(p0_dma_runtime_set_detection_config(&runtime, &config) == 0 && config.generation == 0);
    before = config;
    mode = 1;
    assert(p0_dma_runtime_get_detection_config(&runtime, &config) == -1 && errno == EOPNOTSUPP);
    config = before; mode = 2;
    assert(p0_dma_runtime_set_detection_config(&runtime, &config) == -1 && errno == ESTALE);
    mode = 3;
    assert(p0_dma_runtime_get_detection_config(&runtime, &config) == -1 && errno == EPROTO);
    config = before;
    assert(p0_dma_runtime_set_detection_config(&runtime, &config) == -1 && errno == EPROTO);
    config = before; mode = 4;
    assert(p0_dma_runtime_set_detection_config(&runtime, &config) == -1 && errno == EPROTO);
    config = before; mode = 5;
    assert(p0_dma_runtime_set_detection_config(&runtime, &config) == -1 && errno == EPROTO);
    mode = 0; config = before;
    previous_calls = calls;
    config.alpha_q32 = 0;
    assert(p0_dma_runtime_set_detection_config(&runtime, &config) == -1 && errno == EINVAL);
    config = before; config.weak_alpha_q32 = UINT64_C(1) << 34;
    assert(p0_dma_runtime_set_detection_config(&runtime, &config) == -1 && errno == EINVAL);
    config = before; config.alpha_q32 = UINT64_C(1) << 36;
    assert(p0_dma_runtime_set_detection_config(&runtime, &config) == -1 && errno == EINVAL);
    config = before; config.alpha_q32 = UINT64_C(1) << 32;
    assert(p0_dma_runtime_set_detection_config(&runtime, &config) == -1 && errno == EINVAL);
    assert(p0_dma_runtime_get_detection_config(NULL, &config) == -1 && errno == EINVAL);
    assert(p0_dma_runtime_set_detection_config(&runtime, NULL) == -1 && errno == EINVAL);
    assert(calls == previous_calls);
    mode = 0;
    assert(p0_dma_runtime_get_detection_profile(&runtime, &profile) == 0);
    assert(profile.generation == 9 && profile.fft_size == 8192U);
    profile_before = profile;
    profile.fft_size = 16384U;
    assert(p0_dma_runtime_set_detection_profile(&runtime, &profile) == 0);
    assert(profile.generation == 10 && profile.fft_size == 16384U);
    previous_calls = calls;
    profile = profile_before; profile.fft_size = 2048U;
    assert(p0_dma_runtime_set_detection_profile(&runtime, &profile) == -1 && errno == EINVAL);
    profile = profile_before; profile.reserved = 1U;
    assert(p0_dma_runtime_set_detection_profile(&runtime, &profile) == -1 && errno == EINVAL);
    assert(p0_dma_runtime_get_detection_profile(NULL, &profile) == -1 && errno == EINVAL);
    assert(calls == previous_calls);
    puts("DETECTION_CONFIG_API_PASS");
    return 0;
}
