SUMMARY = "P0 fiziksel AXI DMA istemcisi"
DESCRIPTION = "Coherent tamponlu direct-mode AXI DMA kernel istemcisi ve golden-frame aracı"
LICENSE = "CLOSED"

SRC_URI = "file://Makefile \
           file://p0_dma_client.c \
           file://p0_dma_run.c \
           file://p0_dma_uapi.h \
          "

S = "${WORKDIR}"

inherit module

do_compile:append() {
    ${CC} ${CPPFLAGS} ${CFLAGS} -I${S} ${S}/p0_dma_run.c ${LDFLAGS} -o ${S}/p0-dma-run
}

do_install:append() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/p0-dma-run ${D}${bindir}/p0-dma-run
}

FILES:${PN} += "${bindir}/p0-dma-run"
RDEPENDS:${PN} += "kernel-module-p0-dma-client"
KERNEL_MODULE_AUTOLOAD += "p0_dma_client"
