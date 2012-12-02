pPub 1.1
=========
Version 1.1 by Thanasis Georgiou (sakisds.s@gmail.com)

Description
-----------
pPub is a simple epub reader written in Python using GTK3 and WebKit. It has most features expected from a book reader and some support for ebook-convert. It's licenced under GPLv2.

Features
--------
- Bookmarks use MD5 hashes so filenames are irrelevant.
- Keyboard shortcuts.
- Table of contents support.
- Night mode and custom user CSS support.
- Javascript toggle.
- Basic support for ebook-convert.
- Support for files that don't pass epubcheck.
- Lightweight.

Here is a [screenshot](http://dl.dropbox.com/u/11392968/ppub.png).


Installation
------------
- For Archlinux: Install ppub from AUR.
- For Salix: slapt-src -i ppub
- For other distros: Place ppub inside /usr/bin and everything else inside /usr/share/ppub/. There are optional icons and .desktop files inside ./misc.

Configuration
-------------
Most features can be configured from inside the application with these exceptions:
- cachedir = Path to cache, default is /tmp/ppub-cache-username. If you change this, keep the trailing '/'.
- usercss = Path to custom CSS folder. Each file in that folder will appear as a separate menu entry. If invalid or 'None', custom CSS is disabled.
Config is saved at ~/.ppub.conf. Bookmarks are stored inside the same file.

Help:
-----------
If you find a book that does not work, please extract it (like a zip file) and attach any .opf or .ncx it has inside to your bug report. These will help me resolve the problem. Also feel free to email me requests.

Contributors:
-----------
-Tristan Rice (https://github.com/d4l3k)
-ehainry (https://github.com/ehainry)
-Laurent Bigonville (https://github.com/bigon)
-Laurent Peuch (https://github.com/Psycojoker)

Thanks for trying pPub out!
