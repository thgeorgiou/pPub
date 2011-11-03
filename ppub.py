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

from gi.repository import Gdk, Gtk, WebKit
import os
import shutil
import sys
import re
import xml.sax.handler
import ConfigParser
import hashlib
import getpass

def xml2obj(src): #Converts xml to an object
    non_id_char = re.compile('[^_0-9a-zA-Z]')
    def _name_mangle(name):
        return non_id_char.sub('_', name)

    class DataNode(object):
        def __init__(self):
            self._attrs = {}    # XML attributes and child elements
            self.data = None    # child text data
        def __len__(self):
            # treat single element as a list of 1
            return 1
        def __getitem__(self, key):
            if isinstance(key, basestring):
                return self._attrs.get(key,None)
            else:
                return [self][key]
        def __contains__(self, name):
            return self._attrs.has_key(name)
        def __nonzero__(self):
            return bool(self._attrs or self.data)
        def __getattr__(self, name):
            if name.startswith('__'):
                # need to do this for Python special methods???
                raise AttributeError(name)
            return self._attrs.get(name,None)
        def _add_xml_attr(self, name, value):
            if name in self._attrs:
                # multiple attribute of the same name are represented by a list
                children = self._attrs[name]
                if not isinstance(children, list):
                    children = [children]
                    self._attrs[name] = children
                children.append(value)
            else:
                self._attrs[name] = value
        def __str__(self):
            return self.data or ''
        def __repr__(self):
            items = sorted(self._attrs.items())
            if self.data:
                items.append(('data', self.data))
            return u'{%s}' % ', '.join([u'%s:%s' % (k,repr(v)) for k,v in items])

    class TreeBuilder(xml.sax.handler.ContentHandler):
        def __init__(self):
            self.stack = []
            self.root = DataNode()
            self.current = self.root
            self.text_parts = []
        def startElement(self, name, attrs):
            self.stack.append((self.current, self.text_parts))
            self.current = DataNode()
            self.text_parts = []
            # xml attributes --> python attributes
            for k, v in attrs.items():
                self.current._add_xml_attr(_name_mangle(k), v)
        def endElement(self, name):
            text = ''.join(self.text_parts).strip()
            if text:
                self.current.data = text
            if self.current._attrs:
                obj = self.current
            else:
                # a text only node is simply represented by the string
                obj = text or ''
            self.current, self.text_parts = self.stack.pop()
            self.current._add_xml_attr(_name_mangle(name), obj)
        def characters(self, content):
            self.text_parts.append(content)

    builder = TreeBuilder()
    if isinstance(src,basestring):
        xml.sax.parseString(src, builder)
    else:
        xml.sax.parse(src, builder)
    return builder.root._attrs.values()[0]
    
class Bookmark(Gtk.MenuItem):
    def __init__(self, label, bookmark_id):
        Gtk.MenuItem.__init__(self, label=label)
        self.bookmark_id = bookmark_id
    
class MainWindow: #Main window and it's magic
    def __init__(self):
        #Load configuration
        self.config = ConfigParser.RawConfigParser()
        if os.path.exists(os.path.expanduser(os.path.join("~",".ppub.conf"))):
            self.config.read(os.path.expanduser(os.path.join("~",".ppub.conf")))
        else:
            self.config.add_section("Main")
            self.config.set("Main", "cacheDir", "/tmp/ppub-cache-"+getpass.getuser()+"/")
            self.config.set("Main", "js", "False")
            self.config.set("Main", "caret", "False")
            self.config.set("Main", "usercss", "None")
            self.config.write(open(os.path.expanduser(os.path.join("~",".ppub.conf")), "wb"))
        #Validate configuration
        if not self.config.has_option("Main", "cacheDir"):
            self.config.set("Main", "cacheDir", "/tmp/ppub-cache-"+getpass.getuser()+"/")
        if not self.config.has_option("Main", "js"):
            self.config.set("Main", "js", "False")
        if not self.config.has_option("Main", "caret"):
            self.config.set("Main", "caret", "False")
        if not self.config.has_option("Main", "usercss"):
            self.config.set("Main", "usercss", "None")
            self.user_css_path = self.config.get("Main", "usercss")
        elif not os.path.exists(self.config.get("Main", "usercss")):
            self.user_css_path = "None"
        else:
            self.user_css_path = self.config.get("Main", "usercss")
        
        ##Create UI
        #Window
        self.window = Gtk.Window()
        self.window.set_default_size(800, 600)
        self.window.set_title("pPub")
        self.window.connect("destroy", self.on_exit)
        # Create an accelgroup
        self.accel_group = Gtk.AccelGroup()
        self.window.add_accel_group(self.accel_group)
        #About Window
        self.about_dialog = Gtk.AboutDialog()
        self.about_dialog.set_program_name("pPub")
        self.about_dialog.set_version("0.3")
        self.about_dialog.set_copyright("by Thanasis Georgiou")
        self.about_dialog.set_license("""pPub is free software; you can redistribute it and/or modify it under the \nterms of the GNU General Public Licence as published by the Free Software Foundation.

pPub is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; \nwithout even the implied warranty of \nMERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public Licence for more details.

You should have received a copy of the GNU General Public Licence along \nwith pPub; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, \nFifth Floor, Boston, MA 02110-1301, USA.
        """)
        self.about_dialog.connect("response", self.on_hide_about)
        #Container
        container = Gtk.VBox()
        self.window.add(container)
        
        #Menu bar
        menubar = Gtk.MenuBar()
        container.pack_start(menubar, False, False, 0)
        
        ##File Menu
        file_menu = Gtk.Menu()
        
        #Create items
        menu_open = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_OPEN, None)
        file_menu_sep = Gtk.SeparatorMenuItem.new()
        file_menu_sep.set_sensitive(True)
        menu_exit = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT, None)
        
        #Add them to menu
        file_menu.append(menu_open)
        file_menu.append(file_menu_sep)
        file_menu.append(menu_exit)
        
        #Actions
        menu_open.connect("activate", self.on_open)
        menu_exit.connect("activate", self.on_exit)
        
        #Accelerators
        menu_open.add_accelerator("activate", self.accel_group, ord("O"), Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        menu_exit.add_accelerator("activate", self.accel_group, ord("Q"), Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        
        #Add menu to menubar
        file_m = Gtk.MenuItem(label="File")
        file_m.set_submenu(file_menu)
        menubar.append(file_m)
        
        ##Chapter Menu
        go_menu = Gtk.Menu()
        
        #Create items
        self.menu_next_ch = Gtk.MenuItem(label="Next Chapter")
        self.menu_prev_ch = Gtk.MenuItem(label="Previous Chapter")
        self.menu_jump_ch = Gtk.MenuItem(label="Jump to Chapter...")
        
        #Add them to menu
        go_menu.append(self.menu_next_ch)
        go_menu.append(self.menu_prev_ch)
        go_menu.append(self.menu_jump_ch)
        
        #Actions
        self.menu_next_ch.connect("activate", self.on_next_chapter)
        self.menu_prev_ch.connect("activate", self.on_prev_chapter)
        self.menu_jump_ch.connect("activate", self.on_jump_chapter)
        
        #Add menu to menubar
        go_m = Gtk.MenuItem(label="Go")
        go_m.set_submenu(go_menu)
        menubar.append(go_m)
        
        ##View menu
        view_menu = Gtk.Menu()
        
        #Create items
        self.menu_zoom_in = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_ZOOM_IN, None)
        self.menu_zoom_out = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_ZOOM_OUT, None)
        menu_reset_zoom = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_ZOOM_100, None)
        menu_reset_zoom.set_label("Reset zoom level")
        menu_view_sep = Gtk.SeparatorMenuItem.new()
        menu_enable_caret = Gtk.CheckMenuItem(label="Caret")
        menu_enable_js = Gtk.CheckMenuItem(label="Javascript")
        menu_view_sep2 = Gtk.SeparatorMenuItem.new()
        menu_view_styles = Gtk.MenuItem(label="Styles")

        #Styles submenu
        styles_menu = Gtk.Menu()
        
        menu_styles_default = Gtk.RadioMenuItem(label="Default")
        menu_styles_night = Gtk.RadioMenuItem.new_from_widget(menu_styles_default)
        menu_styles_user = Gtk.RadioMenuItem.new_from_widget(menu_styles_default)
        
        menu_styles_default.set_active(True)
        menu_styles_night.set_label("Night")
        menu_styles_user.set_label("User")
        if self.user_css_path == "None":
            menu_styles_user.set_sensitive(False)
        
        styles_menu.append(menu_styles_default)
        styles_menu.append(menu_styles_night)
        styles_menu.append(menu_styles_user)
        
        #0=Def, 1=Night, 2=User
        menu_styles_default.connect("toggled", self.on_change_style, 0)
        menu_styles_night.connect("toggled", self.on_change_style, 1)
        menu_styles_user.connect("toggled", self.on_change_style, 2)
        
        menu_view_styles.set_submenu(styles_menu)
        
        #Add them to menu
        view_menu.append(self.menu_zoom_in)
        view_menu.append(self.menu_zoom_out)
        view_menu.append(menu_reset_zoom)
        view_menu.append(menu_view_sep)
        view_menu.append(menu_enable_caret)
        view_menu.append(menu_enable_js)
        view_menu.append(menu_view_sep2)
        view_menu.append(menu_view_styles)
        
        #Actions
        self.menu_zoom_in.connect("activate", self.on_zoom_in)
        self.menu_zoom_out.connect("activate", self.on_zoom_out)
        menu_reset_zoom.connect("activate", self.on_reset_zoom)
        menu_enable_caret.connect("activate", self.on_toggle_caret)
        menu_enable_js.connect("activate", self.on_toggle_js)
        
        #Accelerators
        self.menu_zoom_in.add_accelerator("activate", self.accel_group, Gtk.accelerator_parse("<Control>KP_Add")[0], Gtk.accelerator_parse("<Control>KP_Add")[1], Gtk.AccelFlags.VISIBLE)
        self.menu_zoom_out.add_accelerator("activate", self.accel_group, Gtk.accelerator_parse("<Control>KP_Subtract")[0], Gtk.accelerator_parse("<Control>KP_Subtract")[1], Gtk.AccelFlags.VISIBLE)
        
        #Add menu to menubar
        view_m = Gtk.MenuItem(label="View")
        view_m.set_submenu(view_menu)
        menubar.append(view_m)
        
        ##Bookmarks Menu
        self.bookmarks_menu = Gtk.Menu()
        self.bookmarks = []
        
        #Create items
        self.menu_add_bookmark = Gtk.MenuItem(label="Add Bookmark")
        self.menu_delete_bookmarks = Gtk.MenuItem(label="Delete Boomarks...")
        bookmarks_menu_sep = Gtk.SeparatorMenuItem.new()
        
        #Add them to menu
        self.bookmarks_menu.append(self.menu_add_bookmark)
        self.bookmarks_menu.append(self.menu_delete_bookmarks)
        self.bookmarks_menu.append(bookmarks_menu_sep)
        
        #Actions
        self.menu_add_bookmark.connect("activate", self.on_add_bookmark)
        self.menu_delete_bookmarks.connect("activate", self.on_delete_bookmarks)
        
        #Accelerators
        self.menu_add_bookmark.add_accelerator("activate", self.accel_group, ord("B"), Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        
        #Add menu to menubar
        bookmarks_m = Gtk.MenuItem(label="Bookmarks")
        bookmarks_m.set_submenu(self.bookmarks_menu)
        menubar.append(bookmarks_m)
        
        ##Help menu
        help_menu = Gtk.Menu()
        
        #Create items
        menu_about = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_ABOUT, None)
        
        #Add them to menu
        help_menu.append(menu_about)
        
        #Actions
        menu_about.connect("activate", self.on_about)
        
        #Add menu to menubar
        help_m = Gtk.MenuItem(label="Help")
        help_m.set_submenu(help_menu)
        menubar.append(help_m)
        
        #Scrollable Window for Viewer
        self.scr_window = Gtk.ScrolledWindow()
        self.scr_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scr_window.get_vscrollbar().connect("show", self.check_current_bookmark)
        container.pack_end(self.scr_window, True, True, 0)
        
        ##Viewer (pywebgtk)
        self.viewer = Viewer()
        self.viewer.load_uri("about:blank")
        
        #Actions
        self.viewer.connect("key-press-event", self.on_keypress_viewer)
        
        #Default option
        self.current_bookmark = 0
        
        #Add to window
        self.scr_window.add(self.viewer)
        
        #Show window
        self.window.show_all()
        
        #Create a content provider
        self.provider = ContentProvider(self.config)
        
        #Load settings from config
        settings = self.viewer.get_settings()
        if self.config.get("Main", "js") == "True":
            menu_enable_js.set_active(True)
        else:
            menu_enable_js.set_active(False)
        if self.config.get("Main", "caret") == "True":
            menu_enable_caret.set_active(True)
        else:
            menu_enable_caret.set_active(False)
        
        #Check if there are any command line arguments
        if len(sys.argv) == 2:
            #Load book
            if self.provider.prepare_book(sys.argv[1]) == True:
                self.viewer.load_uri("file://"+self.provider.get_chapter_file(0))
                #Change window properties
                self.update_go_menu()
                self.window.set_title(str(self.provider.book_name)+" by "+str(self.provider.book_author))
                self.menu_jump_ch.set_sensitive(True)
                self.enable_bookmark_menus()
                self.update_bookmarks_menu()
                bookmarks_m.set_submenu(self.bookmarks_menu)
            else:
                self.disable_menus()
        else:
            self.disable_menus()
    
    def disable_menus(self): #Disables menus that should be active only while reading
        self.menu_next_ch.set_sensitive(False)
        self.menu_prev_ch.set_sensitive(False)
        self.menu_jump_ch.set_sensitive(False)
        self.menu_add_bookmark.set_sensitive(False)
        self.menu_delete_bookmarks.set_sensitive(False)
    
    def enable_bookmark_menus(self): #Enables bookmarks menu items
        self.menu_add_bookmark.set_sensitive(True)
        self.menu_delete_bookmarks.set_sensitive(True)
        
    def update_go_menu(self): #Updates go menu (disables and enables items)
        if self.provider.current_chapter == self.provider.get_chapter_count():
            self.menu_next_ch.set_sensitive(False)
        else:
            self.menu_next_ch.set_sensitive(True)
        if self.provider.current_chapter == 0:
            self.menu_prev_ch.set_sensitive(False)
        else:
            self.menu_prev_ch.set_sensitive(True)
    
    def update_zoom_menu(self): #Update zoom menu items
        #Don't zoom if zoom level is over 300%
        if self.viewer.props.zoom_level > 3.0:
            self.menu_zoom_in.set_sensitive(False)
        else:
            #Don't zoom if zoom level is less than 30%
            self.menu_zoom_in.set_sensitive(True)
            if self.viewer.props.zoom_level < 0.3:
                self.menu_zoom_out.set_sensitive(False)
            else:
                self.menu_zoom_out.set_sensitive(True)
            
    def update_bookmarks_menu(self): #Reloads bookmarks
        #Remove old bookmarks from menu
        for x in self.bookmarks:
            x.hide()
            del x    
        self.bookmarks = []
        #Load new ones
        count = int(self.config.get(self.provider.book_md5, "count"))
        i = 0
        while i != count:
            i += 1
            x = Bookmark(str(i)+". Chapter "+str(self.config.get(self.provider.book_md5, str(i)+"-ch")), i)
            x.connect("activate", self.on_open_bookmark)
            self.bookmarks.append(x)
        #Add them to menu
        for x in self.bookmarks:
            self.bookmarks_menu.append(x)
            x.show()
            
    def reload_chapter(self):
        if self.provider.ready:
            self.viewer.load_uri("file://"+self.provider.get_chapter_file(self.provider.current_chapter))
            
    ##Signals
    def on_exit(self, widget, data=None): #Clean cache and exit
        settings = self.viewer.get_settings()
        self.config.set("Main", "js", settings.props.enable_scripts)
        self.config.set("Main", "caret", settings.props.enable_caret_browsing)
        self.config.write(open(os.path.expanduser(os.path.join("~",".ppub.conf")), "wb"))
        cache_dir = self.config.get("Main", "cacheDir")
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        Gtk.main_quit()
            
    def on_next_chapter(self, widget, data=None): #View next chapter
        self.viewer.load_uri("file://"+self.provider.get_chapter_file(self.provider.current_chapter+1))
        self.update_go_menu()

    def on_prev_chapter(self, widget, data=None): #View prev. chapter
        self.viewer.load_uri("file://"+self.provider.get_chapter_file(self.provider.current_chapter-1))
        self.update_go_menu()
    
    def on_zoom_in(self, widget, data=None): #Zooms in
        self.viewer.props.zoom_level = self.viewer.props.zoom_level + 0.1
        self.update_zoom_menu()
    
    def on_zoom_out(self, widget, data=None): #Zooms out
        self.viewer.props.zoom_level = self.viewer.props.zoom_level - 0.1
        self.update_zoom_menu()
    
    def on_reset_zoom(self, widget, data=None): #Resets zoom
        self.viewer.props.zoom_level = 1.0
        self.update_zoom_menu()
        
    def on_toggle_caret(self, widget, data=None): #Toggles caret browsing
        settings = self.viewer.get_settings()
        settings.props.enable_caret_browsing = widget.get_active()
    
    def on_toggle_js(self, widget, data=None): #Toggles javascript
        settings = self.viewer.get_settings()
        settings.props.enable_scripts = widget.get_active()
        self.reload_chapter()
    
    def on_change_style(self, widget, data): #0=Def, 1=Night, 2=User
        settings = self.viewer.get_settings()
        if data == 0:
            settings.props.user_stylesheet_uri = ""
        elif data == 1:
            settings.props.user_stylesheet_uri = "file:///usr/share/ppub/night.css"
        else:
            settings.props.user_stylesheet_uri = "file:///usr/share/ppub/night.css"
        self.reload_chapter()
                        
    def on_add_bookmark(self, widget, data=None): #Adds a bookmark
        md5_hash = self.provider.book_md5
        current_bookmark = int(self.config.get(md5_hash, "count"))+1
        self.config.set(md5_hash, "count", current_bookmark)
        self.config.set(md5_hash, str(current_bookmark)+"-ch", self.provider.current_chapter)
        self.config.set(md5_hash, str(current_bookmark)+"-pos", self.scr_window.get_vadjustment().get_value())
        self.update_bookmarks_menu()
   
    def on_open_bookmark(self, widget, data=None):
        bookmark = widget.bookmark_id
        chapter = int(self.config.get(self.provider.book_md5, str(bookmark)+"-ch"))
        pos = float(self.config.get(self.provider.book_md5, str(bookmark)+"-pos"))
        #Load current chapter
        self.current_bookmark = pos
        self.viewer.load_uri("file://"+self.provider.get_chapter_file(chapter))
        
    def check_current_bookmark(self, widget, data=None): #Scroll to bookmark if needed
        if self.current_bookmark != 0:
            self.scr_window.get_vadjustment().set_value(self.current_bookmark)
            self.current_bookmark = 0
    
    def on_delete_bookmarks(self, widget, data=None): #Shows delete bookmarks dialog
        dialog = DeleteBookmarksDialog(self.config, self.provider.book_md5, self.dialog_bookmarks_activated)
        dialog.run()
    
    def dialog_bookmarks_activated(self, widget, data, row=None):
        #Delete bookmark
        bookmark_id = data.get_indices()[0] + 1
        self.config.remove_option(self.provider.book_md5, str(bookmark_id)+"-ch")
        self.config.remove_option(self.provider.book_md5, str(bookmark_id)+"-pos")
        
        #Rewrite all other bookmarks with correct numbering
        count = int(self.config.get(self.provider.book_md5, "count"))
        self.config.set(self.provider.book_md5, "count", count-1)
        old_data_ch = []
        old_data_pos = []
        i = 0
        
        #Save all bookmarks in temporary space
        while i != count:
            i += 1
            if i != bookmark_id:
                old_data_ch.append(self.config.get(self.provider.book_md5, str(i)+"-ch"))
                old_data_pos.append(self.config.get(self.provider.book_md5, str(i)+"-pos"))
                #Delete bookmark from file
                self.config.remove_option(self.provider.book_md5, str(i)+"-ch")
                self.config.remove_option(self.provider.book_md5, str(i)+"-pos")
        i = 0
        #Rewrite them to config
        while i != count-1:
            i += 1
            self.config.set(self.provider.book_md5, str(i)+"-ch", old_data_ch[i-1])
            self.config.set(self.provider.book_md5, str(i)+"-pos", old_data_pos[i-1])
        del old_data_ch
        del old_data_pos
        
        #Update the menu
        self.update_bookmarks_menu()
        #Save config
        self.config.write(open(os.path.expanduser(os.path.join("~",".ppub.conf")), "wb"))
            
    def on_jump_chapter(self, widget, data=None): #Jump to given chapters
        dialog = JumpChapterDialog()        
        answer = dialog.run()
        #Check if answer is actually a chapter
        if answer == 0:
            input_data = int(dialog.get_text())
            dialog.destroy()
            #and act
            if input_data <= self.provider.get_chapter_count:
                self.viewer.load_uri("file://"+self.provider.get_chapter_file(input_data))
            else:
                error_dialog =  Gtk.MessageDialog(None, Gtk.DIALOG_MODAL, Gtk.MESSAGE_ERROR, Gtk.BUTTONS_OK, "Invalid chapter number.")
                error_dialog.run()
                error_dialog.destroy()
        else:
            dialog.destroy()
    
    def on_about(self, widget, data=None): #Show about screen
        self.about_dialog.show()
        
    def on_hide_about(self, widget, data=None): #Hide about screen
        self.about_dialog.hide()
    
    def on_keypress_viewer(self, widget, data): #Change chapters on right/left
        keyval = Gdk.keyval_name(data.keyval)
        if keyval == "Right" and self.menu_next_ch.get_sensitive():
            self.on_next_chapter(widget)
        elif keyval == "Left" and self.menu_prev_ch.get_sensitive():
            self.on_prev_chapter(widget)
            
    def on_open(self, widget, data=None): #Show open dialog
        dialog = OpenDialog("Select book...", None, Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK), self.open_book)
        dialog.run()
    
    def open_book(self, widget=None, data=None): #Open book (from dialog)
        filename = widget.get_filename()
        widget.destroy()
        if self.provider.prepare_book(filename) == True:
            self.viewer.load_uri("file://"+self.provider.get_chapter_file(0))
            self.update_go_menu()
            self.enable_bookmark_menus()
            self.update_bookmarks_menu()
            
            #Set window properties
            self.window.set_title(str(self.provider.book_name)+" by "+str(self.provider.book_author))
            self.menu_jump_ch.set_sensitive(True)   
        else:
            self.viewer.load_uri("about:blank")
            self.window.set_title("pPub")
            self.disable_menus()
            
class Viewer(WebKit.WebView): #Renders the book
    def __init__(self):
        WebKit.WebView.__init__(self)
        settings = self.get_settings()
        self.set_full_content_zoom(True)
        settings.props.enable_scripts = False
        settings.props.enable_plugins = False
        settings.props.enable_page_cache = False
        settings.props.enable_java_applet = False
        #settings.props.user_stylesheet_uri = "file://~/style.css"
        try:
            settings.props.enable_webgl = False
        except AttributeError:
            pass
        settings.props.enable_default_context_menu = False
        settings.props.enable_html5_local_storage = False

class ContentProvider(): #Manages book files and provides metadata
    def __init__(self, config):
        #Check if needed folder exists
        self.config = config
        self.cache_path = self.config.get("Main", "cacheDir")
        if not os.path.exists(self.cache_path):
            os.mkdir(self.cache_path)
        self.ready = False
        
    def prepare_book(self, filepath):
        #Clear any old files from the cache and extract the current book 
        if os.path.exists(self.cache_path):
            shutil.rmtree(self.cache_path)
            
        #Extract book
        os.system("unzip -d "+self.cache_path+" \""+filepath+"\"")
        #Set permissions
        os.system("chmod 700 "+self.cache_path)
        
        #Find opf file
        if os.path.exists(self.cache_path+"META-INF/container.xml"):
            container_data = xml2obj(open(self.cache_path+"META-INF/container.xml", "r"))
            opf_file_path = container_data.rootfiles.rootfile.full_path
            #Load opf
            metadata = xml2obj(open(self.cache_path+opf_file_path, "r")) #Load metadata
            self.files = []
            #Files
            for x in metadata.manifest.item:
                if x.media_type == "application/xhtml+xml":
                     self.files.append(x.href)
            self.oebps = os.path.split(opf_file_path)[0]       
            #Calculate MD5 of book (for bookmarks)
            md5 = hashlib.md5()
            with open(filepath,'rb') as f: 
                for chunk in iter(lambda: f.read(128*md5.block_size), ''): 
                    md5.update(chunk)
            #Metadata
            try:
                self.book_name = metadata.metadata.dc_title
                self.book_author = metadata.metadata.dc_creator
            except UnicodeEncodeError:
                self.book_name = "Unknown"
                self.book_author = "Unknown"
                print "Warning: Could not read book metadata."
            self.book_md5 = md5.hexdigest()
            
            #Add book to config
            if not self.config.has_section(self.book_md5):
                self.config.add_section(self.book_md5)
                self.config.set(self.book_md5, "count", 0) 
            #End of preparations
            self.ready = True
            return True
        else: #Else show an error dialog
            error_dialog =  Gtk.MessageDialog(None, Gtk.DIALOG_MODAL, Gtk.MESSAGE_ERROR, Gtk.BUTTONS_OK, "Cannot open file.")
            error_dialog.run()
            error_dialog.destroy()
            self.ready = False
            return False
        
    def get_chapter_file(self, number): #Returns a chapter file
        self.current_chapter = number
        return self.cache_path+"/"+self.oebps+"/"+self.files[number]
    
    def get_chapter_count(self): #Returns number of chapters
        return len(self.files)-1
        
    def get_status(self):
        return self.ready

class OpenDialog(Gtk.FileChooserDialog): #File>Open dialog
    def __init__(self, title, none, action, buttons, activate):
        super(OpenDialog, self).__init__(title, none, action, buttons)
        #Prepare filters
        filter_pub = Gtk.FileFilter()
        filter_pub.set_name("EPub files")
        filter_pub.add_pattern("*.epub")
        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")
        #Add filters
        self.add_filter(filter_pub)
        self.add_filter(filter_all)
        
        #Activation response
        self.activate = activate
        #Prepare dialog
        self.set_default_response(Gtk.ResponseType.OK)
        self.connect("file-activated", self.activate)
        self.connect("response", self.respond)
        
    def respond(self, widget, data=None): #Check response
        if data == (-5):
            self.activate(widget, data)
        else:
            self.destroy()

class JumpChapterDialog(Gtk.Dialog): #Chapters>Jump dialog
    def __init__(self):
        super(JumpChapterDialog, self).__init__()        
        label = Gtk.Label("Enter chapter number:")
        label.show()
        #self.vbox = self.get_content_area()
        self.vbox.pack_start(label, True, True, 0)
        #Create entry box
        self.entry = Gtk.Entry()
        self.entry.show()
        self.entry.connect("activate", self.on_dialog_enter)
        self.vbox.pack_start(self.entry, True, True, 0)
        #Add buttons
        self.add_button(Gtk.STOCK_OK, 0)
        self.add_button(Gtk.STOCK_CANCEL, 1)
        self.set_default_response(0)

    def get_text(self): #Returns text in entry box
        return self.entry.get_text()
    
    def run(self): #Shows dialog
        answer = super(JumpChapterDialog, self).run()
        if answer == 0:
            if self.entry.get_text() != "":
                return 0
            else:
                return 1
        else:
            return 1
        
    def on_dialog_enter(self, widget, data=None): #Closes "jump to" dialog when enter is pressed
        if self.entry.get_text() != "":
            self.response(0)
        else:
            self.response(1)

class DeleteBookmarksDialog(Gtk.Dialog):
    def __init__(self, config, book_md5, action):
        #Window
        super(DeleteBookmarksDialog, self).__init__()
        self.set_title("Bookmarks")
        self.config = config
        self.book_md5 = book_md5
        self.set_size_request(350, 250)
        self.activation_action = action
        #Label
        label = Gtk.Label("Double click a bookmark to delete.")
        self.vbox.pack_start(label, False, False, 0)
        #Scrollable Area
        self.scr_window = Gtk.ScrolledWindow()
        self.scr_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scr_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.vbox.pack_end(self.scr_window, True, True, 0)
        #Tree view
        self.refresh_tree()
        #Buttons
        self.add_button(Gtk.STOCK_CLOSE, 0)
        self.set_default_response(0)
        #Show all these stuff
        self.vbox.show_all()
        
    def refresh_tree(self, widget=None, data=None, row=None): #Refresh bookmarks view
        if widget != None:
            self.scr_window.remove(self.tree)
        store = self.create_model()
        self.tree = Gtk.TreeView(model=store)
        self.create_columns(self.tree)
        self.tree.connect("row-activated", self.activation_action)
        self.tree.connect("row-activated", self.refresh_tree)
        self.tree.set_rules_hint(True)
        #Re-add control
        self.scr_window.add(self.tree)
        self.tree.show()
        
    def create_model(self): #Load data
        store = Gtk.ListStore(int, str)
        #Parse bookmarks from config
        count = int(self.config.get(self.book_md5, "count"))
        i = 0
        while i != count:
            i += 1
            store.append((i, "Chapter "+str(self.config.get(self.book_md5, str(i)+"-ch"))))
        return store

    def create_columns(self, tree_view): #Create columns for tree view
        #Number column
        renderer_text = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Number", renderer_text, text=0)
        column.set_sort_column_id(0)    
        tree_view.append_column(column)
        #Chapter column
        renderer_text = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Chapter", renderer_text, text=1)
        column.set_sort_column_id(1)
        tree_view.append_column(column)
    
    def run(self): #Show dialog
        answer = super(DeleteBookmarksDialog, self).run()
        if answer == 0 or answer == -4:
            self.destroy()
        else:
            self.activation_action(self)
            
main = MainWindow()
Gtk.main()
