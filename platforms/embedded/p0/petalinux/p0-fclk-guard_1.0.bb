SUMMARY = "P0 FCLK0 guarded runtime alignment helper"
DESCRIPTION = "Read-only-by-default CCF FCLK0 guard; it is never auto-loaded."
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://p0_fclk_guard.c;beginline=1;endline=1;md5=fcab174c20ea2e2bc0be64b493708266"

SRC_URI = "file://p0_fclk_guard.c \
           file://p0_fclk_guard_logic.h \
           file://p0_fclk_guard_uapi.h \
           file://p0-fclk-guard.Makefile \
          "

S = "${WORKDIR}"

inherit module

do_configure:prepend() {
    install -m 0644 ${S}/p0-fclk-guard.Makefile ${S}/Makefile
}

do_compile() {
    oe_runmake -C ${STAGING_KERNEL_BUILDDIR} M=${S} modules
}

do_install() {
    install -d ${D}${nonarch_base_libdir}/modules/${KERNEL_VERSION}/updates
    install -m 0644 ${S}/p0_fclk_guard.ko \
        ${D}${nonarch_base_libdir}/modules/${KERNEL_VERSION}/updates/p0_fclk_guard.ko
}

FILES:${PN} += "${nonarch_base_libdir}/modules/${KERNEL_VERSION}/updates/p0_fclk_guard.ko"
