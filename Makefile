PREFIX ?= /usr
PPUBDIR = ${PREFIX}/share/ppub
BINDIR = ${PREFIX}/bin
PYTHON ?= ${BINDIR}/python2

all: ppub

ppub:
	sed 's|PREFIX|${PREFIX}|' ppub.py.in > ppub.py
	echo "#!/bin/sh" > ppub
	echo "${PYTHON} ${PPUBDIR}/ppub.py \"\$$@\"" >> ppub

install: install-bin install-desktop

install-bin: ppub
	install -d ${BINDIR}
	install -d ${PPUBDIR}
	install ppub ${BINDIR}
	install -m 644 contentprovider.py ${PPUBDIR}/contentprovider.py
	install -m 644 dialogs.py ${PPUBDIR}/dialogs.py
	install -m 644 night.css ${PPUBDIR}/night.css
	install -m 644 ppub.py ${PPUBDIR}/ppub.py
	install -m 644 xml2obj.py ${PPUBDIR}/xml2obj.py

install-desktop:
	install -d ${PREFIX}/share/icons/hicolor/24x24/apps
	install -d ${PREFIX}/share/icons/hicolor/32x32/apps
	install -d ${PREFIX}/share/icons/hicolor/48x48/apps
	install -d ${PREFIX}/share/icons/hicolor/64x64/apps
	install -d ${PREFIX}/share/icons/hicolor/scalable/apps
	install -d ${PREFIX}/share/applications
	install -m644 misc/ppub-24.png \
		${PREFIX}/share/icons/hicolor/24x24/apps/ppub.png
	install -m644 misc/ppub-32.png \
		${PREFIX}/share/icons/hicolor/32x32/apps/ppub.png
	install -m644 misc/ppub-48.png \
		${PREFIX}/share/icons/hicolor/48x48/apps/ppub.png
	install -m644 misc/ppub-64.png \
		${PREFIX}/share/icons/hicolor/64x64/apps/ppub.png
	install -m644 misc/ppub-scalable.svg \
		${PREFIX}/share/icons/hicolor/scalable/apps/ppub.svg
	install -m644 misc/ppub.desktop \
		${PREFIX}/share/applications/ppub.desktop

clean:
	rm -f ppub ppub.py

uninstall: uninstall-bin uninstall-desktop

uninstall-bin:
	rm -rf ${PPUBDIR}
	rm -rf ${BINDIR}/ppub

uninstall-desktop:
	rm -f ${PREFIX}/share/applications/ppub.desktop
	rm -f ${PREFIX}/share/icons/hicolor/*/apps/ppub.png

.PHONY: all install install-bin install-desktop
