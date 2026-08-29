SUMMARY = "P0 AXI DMA sürücüsü ve yerel ED kart hizmeti"
DESCRIPTION = "Root-only DMA aygıtı, yetkisi düşürülmüş yerel ED hizmeti ve sürümlü istemci"
LICENSE = "CLOSED"

SRC_URI = "file://Makefile \
           file://p0_dma_client.c \
           file://p0_dma_run.c \
           file://p0_dma_uapi.h \
           file://p0_os_cfar.c \
           file://p0_os_cfar.h \
           file://p0_os_cfar_run.c \
           file://p0_pl_os_cfar.c \
           file://p0_pl_os_cfar.h \
           file://p0_multiscale_detector.c \
           file://p0_multiscale_detector.h \
           file://p0_candidate_packet.c \
           file://p0_candidate_packet.h \
           file://p0_ed_runtime_run.c \
           file://phase06i_transport_abi.h \
           file://phase06j_temporal.c \
           file://phase06j_temporal.h \
           file://p0_dma_runtime.c \
           file://p0_dma_runtime.h \
           file://p0_ed_pipeline.c \
           file://p0_ed_pipeline.h \
           file://p0_ed_service_protocol.c \
           file://p0_ed_service_protocol.h \
           file://p0_ed_service.c \
           file://p0_ed_client.c \
           file://p0_ed_throughput_run.c \
           file://p0_ed_stage_profile_run.c \
           file://p0_parameter_runtime.c \
           file://p0_parameter_runtime.h \
           file://p0_parameter_run.c \
           file://p0_parameter_client.c \
           file://p0-ed-service.init \
          "

S = "${WORKDIR}"

inherit module update-rc.d useradd

USERADD_PACKAGES = "${PN}"
GROUPADD_PARAM:${PN} = "--system p0ed"
USERADD_PARAM:${PN} = "--system --home /nonexistent --no-create-home --shell /sbin/nologin --gid p0ed p0ed"

INITSCRIPT_NAME = "p0-ed-service"
INITSCRIPT_PARAMS = "defaults 99"
P0_HOT_PATH_CFLAGS = "-O3"

do_compile:append() {
    ${CC} ${CPPFLAGS} ${CFLAGS} -I${S} ${S}/p0_dma_runtime.c ${S}/p0_dma_run.c ${LDFLAGS} -o ${S}/p0-dma-run
    ${CC} ${CPPFLAGS} ${CFLAGS} ${P0_HOT_PATH_CFLAGS} -I${S} ${S}/p0_os_cfar.c ${S}/p0_os_cfar_run.c ${LDFLAGS} -lm -o ${S}/p0-os-cfar-run
    ${CC} ${CPPFLAGS} ${CFLAGS} ${P0_HOT_PATH_CFLAGS} -I${S} ${S}/p0_os_cfar.c ${S}/p0_multiscale_detector.c ${S}/p0_candidate_packet.c ${S}/phase06j_temporal.c ${S}/p0_ed_runtime_run.c ${LDFLAGS} -lm -o ${S}/p0-ed-runtime-run
    ${CC} ${CPPFLAGS} ${CFLAGS} ${P0_HOT_PATH_CFLAGS} -I${S} ${S}/p0_dma_runtime.c ${S}/p0_parameter_runtime.c ${S}/p0_ed_pipeline.c ${S}/p0_ed_service_protocol.c ${S}/p0_ed_service.c ${S}/p0_os_cfar.c ${S}/p0_pl_os_cfar.c ${S}/p0_multiscale_detector.c ${S}/p0_candidate_packet.c ${S}/phase06j_temporal.c ${LDFLAGS} -lm -o ${S}/p0-ed-service
    ${CC} ${CPPFLAGS} ${CFLAGS} ${P0_HOT_PATH_CFLAGS} -I${S} ${S}/p0_ed_service_protocol.c ${S}/p0_ed_client.c ${LDFLAGS} -o ${S}/p0-ed-client
    ${CC} ${CPPFLAGS} ${CFLAGS} ${P0_HOT_PATH_CFLAGS} -I${S} ${S}/p0_ed_service_protocol.c ${S}/p0_ed_throughput_run.c ${LDFLAGS} -lm -o ${S}/p0-ed-throughput-run
    ${CC} ${CPPFLAGS} ${CFLAGS} ${P0_HOT_PATH_CFLAGS} -I${S} ${S}/p0_dma_runtime.c ${S}/p0_parameter_runtime.c ${S}/p0_ed_pipeline.c ${S}/p0_os_cfar.c ${S}/p0_pl_os_cfar.c ${S}/p0_multiscale_detector.c ${S}/p0_candidate_packet.c ${S}/phase06j_temporal.c ${S}/p0_ed_stage_profile_run.c ${LDFLAGS} -lm -o ${S}/p0-ed-stage-profile-run
    ${CC} ${CPPFLAGS} ${CFLAGS} -I${S} ${S}/p0_parameter_runtime.c ${S}/p0_parameter_run.c ${LDFLAGS} -lm -o ${S}/p0-parameter-run
    ${CC} ${CPPFLAGS} ${CFLAGS} -I${S} ${S}/p0_ed_service_protocol.c ${S}/p0_parameter_client.c ${LDFLAGS} -o ${S}/p0-parameter-client
}

do_install:append() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/p0-dma-run ${D}${bindir}/p0-dma-run
    install -m 0755 ${S}/p0-os-cfar-run ${D}${bindir}/p0-os-cfar-run
    install -m 0755 ${S}/p0-ed-runtime-run ${D}${bindir}/p0-ed-runtime-run
    install -m 0755 ${S}/p0-ed-client ${D}${bindir}/p0-ed-client
    install -m 0755 ${S}/p0-ed-throughput-run ${D}${bindir}/p0-ed-throughput-run
    install -m 0755 ${S}/p0-ed-stage-profile-run ${D}${bindir}/p0-ed-stage-profile-run
    install -m 0755 ${S}/p0-parameter-run ${D}${bindir}/p0-parameter-run
    install -m 0755 ${S}/p0-parameter-client ${D}${bindir}/p0-parameter-client
    install -d ${D}${sbindir}
    install -m 0755 ${S}/p0-ed-service ${D}${sbindir}/p0-ed-service
    install -d ${D}${sysconfdir}/init.d
    install -m 0755 ${S}/p0-ed-service.init ${D}${sysconfdir}/init.d/p0-ed-service
}

FILES:${PN} += "${bindir}/p0-dma-run ${bindir}/p0-os-cfar-run ${bindir}/p0-ed-runtime-run ${bindir}/p0-ed-client ${bindir}/p0-ed-throughput-run ${bindir}/p0-ed-stage-profile-run ${bindir}/p0-parameter-run ${bindir}/p0-parameter-client ${sbindir}/p0-ed-service ${sysconfdir}/init.d/p0-ed-service"
RDEPENDS:${PN} += "kernel-module-p0-dma-client"
KERNEL_MODULE_AUTOLOAD += "p0_dma_client"
