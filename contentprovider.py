#!/usr/bin/env python2

# pPub by Thanasis Georgiou <sakisds@gmx.com>

# pPub is free software; you can redistribute it and/or modify it under the terms
# of the GNU General Public Licence as published by the Free Software Foundation.

# pPub is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public Licence for more details.

# You should have received a copy of the GNU General Public Licence along with
# pPub; if not, write to the Free Software Foundation, Inc., 51 Franklin Street,
# Fifth Floor, Boston, MA 02110-1301, USA.

import hashlib
import zipfile
import os
import shutil
from xml2obj import *

class ContentProvider(): #Manages book files and provides metadata
    def __init__(self, config, window):
        self.window = window
        #Check if cache folder exists
        self.config = config
        self.cache_path = self.config.get("Main", "cacheDir")
        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path) #If not create it
        self.ready = False

    def prepare_book(self, filepath):
        #Clear any old files from the cache
        if os.path.exists(self.cache_path):
            shutil.rmtree(self.cache_path)
        #Extract new book
        zipfile.ZipFile(filepath).extractall(path=self.cache_path)
        #Set permissions
        os.system("chmod 700 "+self.cache_path)

        #Find opf file
        if os.path.exists(self.cache_path+"META-INF/container.xml"):
            container_data = xml2obj(open(self.cache_path+"META-INF/container.xml", "r"))
            opf_file_path = container_data.rootfiles.rootfile.full_path
            #Load opf
            metadata = xml2obj(open(self.cache_path+opf_file_path, "r"))
            self.oebps = os.path.split(opf_file_path)[0]
            #Find ncx file
            for x in metadata.manifest.item:
                if x.media_type == "application/x-dtbncx+xml":
                    ncx_file_path = self.cache_path+"/"+self.oebps+"/"+x.href

            #Load titles and filepaths
            self.titles = []
            self.files = []
            if os.access(ncx_file_path, os.R_OK): #Check if ncx is accessible
                #Parse ncx file
                pat=re.compile('-(.*)-')
                for line in open(ncx_file_path):
                    line=line.strip()
                    if "<text>" in line:
                        out = line.replace("<text>", "")
                        out = out.replace("</text>", "")
                        out = out.replace("<content", "")
                        self.titles.append(out)
                    if "<content" in line:
                        out = line.replace("<content src=\"", "")
                        out = out.replace("\"", "")
                        out = out.replace("/>", "")
                        self.files.append(out)
                while not len(self.titles) == len(self.files):
                    self.titles.remove(self.titles[0])

            #Validate files
            if not os.path.exists(self.cache_path+"/"+self.oebps+"/"+self.files[0]):
                #Reload files
                self.files = []
                for x in metadata.manifest.item:
                    if x.media_type == "application/xhtml+xml":
                        self.files.append(x.href)
                self.titles = []
                i = 1
                while not len(self.titles) == len(self.files):
                    self.titles.append("Chapter "+str(i))
                    i += 1

            #Calculate MD5 of book (for bookmarks)
            md5 = hashlib.md5()
            with open(filepath,'rb') as f: 
                for chunk in iter(lambda: f.read(128*md5.block_size), ''):
                    md5.update(chunk)
            #Metadata
            self.book_name = unicode(metadata.metadata.dc_title).encode("utf-8")
            self.book_author = unicode(metadata.metadata.dc_creator).encode("utf-8")
            self.book_md5 = md5.hexdigest()
            #Add book to config (used for bookmarks)
            if not self.config.has_section(self.book_md5):
                self.config.add_section(self.book_md5)
                self.config.set(self.book_md5, "count", 0)
                self.config.set(self.book_md5, "chapter", 0)
                self.config.set(self.book_md5, "pos", 0.0)
                self.config.set(self.book_md5, "stylesheet","")

            #End of preparations
            self.ready = True
            return True
        else: #Else show an error dialog
            error_dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK, "Could not open book.")
            error_dialog.format_secondary_text("Make sure the book you are trying to open is in supported format and try again.")
            error_dialog.run()
            error_dialog.destroy()
            self.ready = False
            return False

    def get_chapter_file(self, number): #Returns a chapter file (for viewer)
        return self.cache_path+"/"+self.oebps+"/"+self.files[number]

    def get_chapter_count(self): #Returns number of chapters
        return len(self.files)-1

    def get_status(self):
        return self.ready
