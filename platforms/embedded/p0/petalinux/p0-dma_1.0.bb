SUMMARY = "P0 fiziksel AXI DMA istemcisi"
DESCRIPTION = "Coherent tamponlu direct-mode AXI DMA kernel istemcisi ve golden-frame aracı"
LICENSE = "CLOSED"

SRC_URI = "file://Makefile \
           file://p0_dma_client.c \
           file://p0_dma_run.c \
           file://p0_dma_uapi.h \
           file://p0_os_cfar.c \
           file://p0_os_cfar.h \
           file://p0_os_cfar_run.c \
           file://p0_candidate_packet.c \
           file://p0_candidate_packet.h \
           file://p0_ed_runtime_run.c \
           file://phase06i_transport_abi.h \
           file://phase06j_temporal.c \
           file://phase06j_temporal.h \
          "

S = "${WORKDIR}"

inherit module

do_compile:append() {
    ${CC} ${CPPFLAGS} ${CFLAGS} -I${S} ${S}/p0_dma_run.c ${LDFLAGS} -o ${S}/p0-dma-run
    ${CC} ${CPPFLAGS} ${CFLAGS} -I${S} ${S}/p0_os_cfar.c ${S}/p0_os_cfar_run.c ${LDFLAGS} -lm -o ${S}/p0-os-cfar-run
    ${CC} ${CPPFLAGS} ${CFLAGS} -I${S} ${S}/p0_os_cfar.c ${S}/p0_candidate_packet.c ${S}/phase06j_temporal.c ${S}/p0_ed_runtime_run.c ${LDFLAGS} -lm -o ${S}/p0-ed-runtime-run
}

do_install:append() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/p0-dma-run ${D}${bindir}/p0-dma-run
    install -m 0755 ${S}/p0-os-cfar-run ${D}${bindir}/p0-os-cfar-run
    install -m 0755 ${S}/p0-ed-runtime-run ${D}${bindir}/p0-ed-runtime-run
}

FILES:${PN} += "${bindir}/p0-dma-run ${bindir}/p0-os-cfar-run ${bindir}/p0-ed-runtime-run"
RDEPENDS:${PN} += "kernel-module-p0-dma-client"
KERNEL_MODULE_AUTOLOAD += "p0_dma_client"
