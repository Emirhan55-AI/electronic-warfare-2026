SUMMARY = "P0 FCLK guard userspace control tool"
DESCRIPTION = "Explicit ioctl client for p0-fclk-guard; it does not autoload the module."
LICENSE = "GPL-2.0-only"
LIC_FILES_CHKSUM = "file://p0_fclk_guardctl.c;beginline=1;endline=1;md5=fcab174c20ea2e2bc0be64b493708266"

SRC_URI = "file://p0_fclk_guardctl.c \
           file://p0_fclk_guard_uapi.h \
          "

S = "${WORKDIR}"

do_compile() {
    ${CC} ${CPPFLAGS} ${CFLAGS} -I${S} ${S}/p0_fclk_guardctl.c \
        ${LDFLAGS} -o ${S}/p0-fclk-guard
}

do_install() {
    install -d ${D}${bindir}
    install -m 0755 ${S}/p0-fclk-guard ${D}${bindir}/p0-fclk-guard
}

FILES:${PN} += "${bindir}/p0-fclk-guard"
