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

import os
import shutil
import sys
import ConfigParser
import getpass
import threading
from gi.repository import Gdk, Gtk, GObject, WebKit
from dialogs import *
from contentprovider import *

class Bookmark(Gtk.MenuItem): #Bookmark storing object
    def __init__(self, label, bookmark_id):
        Gtk.MenuItem.__init__(self, label=label)
        self.bookmark_id = bookmark_id

class Viewer(WebKit.WebView): #Renders the book (webkit viewer)
    def __init__(self):
        WebKit.WebView.__init__(self)
        settings = self.get_settings()
        self.set_full_content_zoom(True)
        settings.props.enable_scripts = False
        settings.props.enable_plugins = False
        settings.props.enable_page_cache = False
        settings.props.enable_java_applet = False
        try:
            settings.props.enable_webgl = False
        except AttributeError:
            pass
        settings.props.enable_default_context_menu = False
        settings.props.enable_html5_local_storage = False

class MainWindow: #Main window
    def __init__(self):
        #Create Window
        settingsgtk = Gtk.Settings()
        settingsgtk.props.gtk_application_prefer_dark_theme = True
        self.window = Gtk.Window()
        self.window.set_default_size(800, 600)
        self.window.set_title("pPub")
        self.window.connect("destroy", self.on_exit)

        #Load configuration
        self.config = ConfigParser.RawConfigParser()
        config_path = os.path.expanduser(os.path.join("~",".ppub.conf"))
        if os.access(config_path, os.W_OK): #If a config file exists...
            self.config.read(config_path) #...load it.
        else: #Else create a new one
            self.config.add_section("Main")
            self.config.set("Main", "cacheDir",
                            "/tmp/ppub-cache-"+getpass.getuser()+"/")
            self.config.set("Main", "js", "False")
            self.config.set("Main", "caret", "False")
            self.config.set("Main", "usercss", "None")
            try:
                self.config.write(open(config_path, "wb"))
            except:
                error_dialog = Gtk.MessageDialog(self.window, 0,
                                                 Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
                                                 "Could not write configuration file.")
                error_dialog.format_secondary_text("Make sure ~/.ppub is accessible and try again.")
                error_dialog.run()
                exit()
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
        elif os.access(self.config.get("Main", "usercss"), os.R_OK):
            # Get dirname of file (should allow backwards compatibility)
            self.user_css_path = os.path.dirname(self.config.get("Main", "usercss"))+'/'
        else:
            self.config.set("Main", "usercss", "None")
            self.user_css_path = self.config.get("Main", "usercss")
        # Set the changes if converting from a previous version.
        self.config.set("Main", "usercss", self.user_css_path)
        #Create Widgets
        #Create an accelgroup
        self.accel_group = Gtk.AccelGroup()
        self.window.add_accel_group(self.accel_group)
        #About Window
        self.about_dialog = Gtk.AboutDialog()
        self.about_dialog.set_program_name("pPub")
        self.about_dialog.set_version("1.0")
        self.about_dialog.set_copyright("by Thanasis Georgiou")
        self.about_dialog.set_license("""pPub is free software; you can redistr\
ibute it and/or modify it under the \nterms of the GNU General Public Licence a\
s published by the Free Software Foundation.\n\npPub is distributed in the hope\
that it will be useful, but WITHOUT ANY WARRANTY; \nwithout even the implied wa\
rranty of \nMERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU G\
eneral Public Licence for more details.\n\nYou should have received a copy of t\
he GNU General Public Licence along \nwith pPub; if not, write to the Free Soft\
ware Foundation, Inc., 51 Franklin Street, \nFifth Floor, Boston, MA 02110-1301\
, USA.  """)
        self.about_dialog.connect("response", self.on_hide_about)

        #Container
        container = Gtk.VBox()
        self.window.add(container)
        #Menu bar
        menubar = Gtk.MenuBar()
        container.pack_start(menubar, False, False, 0)

        #File Menu
        file_menu = Gtk.Menu()
        #Create items
        menu_open = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_OPEN, None)
        menu_import = Gtk.MenuItem(label="Import Book...")
        file_menu_sep = Gtk.SeparatorMenuItem.new()
        file_menu_sep.set_sensitive(True)
        menu_exit = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT, None)
        #Add them to menu
        file_menu.append(menu_open)
        file_menu.append(menu_import)
        file_menu.append(file_menu_sep)
        file_menu.append(menu_exit)
        #Actions
        menu_open.connect("activate", self.on_open)
        menu_import.connect("activate", self.on_import)
        menu_exit.connect("activate", self.on_exit)
        #Accelerators
        menu_open.add_accelerator("activate", self.accel_group, ord("O"), Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        menu_exit.add_accelerator("activate", self.accel_group, ord("Q"), Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE)
        #Add menu to menubar
        file_m = Gtk.MenuItem(label="File")
        file_m.set_submenu(file_menu)
        menubar.append(file_m)
        #Disable import if ebook-convert is not installed
        if not os.path.exists("/usr/bin/ebook-convert"):
            menu_import.set_sensitive(False)

        #Chapter Menu
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

        #View menu
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
        #Labels
        menu_styles_default.set_active(True)
        menu_styles_night.set_label("Night")
        styles_menu.append(menu_styles_default)
        styles_menu.append(menu_styles_night)
        # Adds multiple userstyles from path.
        if self.user_css_path != "None":
            # Iterate through the directory
            for stylesheet in os.listdir(self.config.get("Main", "usercss")):
                # check if css file
                if stylesheet[-4:].lower() == ".css":
	                menu_styles_user = Gtk.RadioMenuItem.new_from_widget(menu_styles_default)
	                menu_styles_user.set_label(stylesheet[0:-4])
	                styles_menu.append(menu_styles_user)
	                menu_styles_user.connect("toggled", self.on_change_style, 2)
        #Add to menu
        #Toggled event: 0=Def, 1=Night, 2=User
        menu_styles_default.connect("toggled", self.on_change_style, 0)
        menu_styles_night.connect("toggled", self.on_change_style, 1)

        #Set submenu
        menu_view_styles.set_submenu(styles_menu)
        #Add to menu
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

        #Contents Menu
        self.empty_contents_menu = Gtk.Menu()
        #Create items
        self.contents_menu_placeholder = Gtk.MenuItem(label='No book loaded')
        self.contents_menu_placeholder.set_sensitive(False)
        self.empty_contents_menu.append(self.contents_menu_placeholder)
        #Add to menubar
        self.contents_m = Gtk.MenuItem(label="Contents")
        self.contents_m.set_submenu(self.empty_contents_menu)
        menubar.append(self.contents_m)

        #Bookmarks Menu
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

        #Help menu
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
        self.scr_window.get_vscrollbar().connect("show", self.check_current_bookmark_scroll)
        container.pack_end(self.scr_window, True, True, 0)

        #Viewer (Webkit)
        self.viewer = Viewer()
        self.viewer.load_uri("about:blank") #Display a blank page
        #Actions
        self.viewer.connect("key-press-event", self.on_keypress_viewer)
        self.viewer.connect("load-finished", self.check_current_bookmark_viewer)
        #Default option
        self.current_bookmark = 0

        #Add to window
        self.scr_window.add(self.viewer)
        #Show window
        self.window.show_all()

        #Create a content provider
        self.provider = ContentProvider(self.config, self.window)
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
            self.load_book(sys.argv[1])
        else:
            self.disable_menus()

    def disable_menus(self): #Disables menus that should be active only while reading
        self.menu_next_ch.set_sensitive(False)
        self.menu_prev_ch.set_sensitive(False)
        self.menu_jump_ch.set_sensitive(False)
        self.menu_add_bookmark.set_sensitive(False)
        self.menu_delete_bookmarks.set_sensitive(False)
        self.contents_m.set_submenu(self.empty_contents_menu)

    def enable_bookmark_menus(self): #Enables bookmarks menu items
        self.menu_add_bookmark.set_sensitive(True)
        self.menu_delete_bookmarks.set_sensitive(True)

    def update_contents_menu(self): #Updates content menu
        if self.provider.ready:
            titles = self.provider.titles
            self.content_menu = Gtk.Menu()

            base_item = Gtk.RadioMenuItem(label=titles[0])
            base_item.connect("toggled", self.contents_menu_change, 0)
            base_item.show()
            self.content_menu.append(base_item)

            #Set the corrent active item
            if self.provider.current_chapter == 0:
                base_item.set_active(True)
                active_item = 0
            else:
                active_item = self.provider.current_chapter
            i = 0
            for x in titles:
                if i == 0:
                    i = 1
                else:
                    item = Gtk.RadioMenuItem.new_from_widget(base_item)
                    item.set_label(x)
                    item.connect("toggled", self.contents_menu_change, i)
                    self.content_menu.append(item)

                    if active_item == i:
                        item.set_active(True)
                    item.show()
                    i += 1
            self.contents_m.set_submenu(self.content_menu)
        else:
            self.contents_m.set_submenu(self.empty_contents_menu)

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
            chapter = int((self.config.get(self.provider.book_md5, str(i)+"-ch")))
            x = Bookmark(str(i)+". "+self.provider.titles[chapter], i)
            x.connect("activate", self.on_open_bookmark)
            self.bookmarks.append(x)
        #Add them to menu
        for x in self.bookmarks:
            self.bookmarks_menu.append(x)
            x.show()

    def load_book(self, filename): #Extracts and prepares book
        if self.provider.prepare_book(filename) == True: #If book is ready
            #Load chapter position
            self.load_chapter_pos()
            #Open book on viewer
            self.viewer.load_uri("file://"+self.provider.get_chapter_file(self.provider.current_chapter))
            #Update menus
            self.enable_bookmark_menus()
            self.update_bookmarks_menu()
            self.update_contents_menu()
            self.update_go_menu()
            #Set window properties
            self.window.set_title(str(self.provider.book_name)+" by "+str(self.provider.book_author))
            self.menu_jump_ch.set_sensitive(True)
        else: #If book is not ready (error?) restore window to defaults
            self.viewer.load_uri("about:blank")
            self.window.set_title("pPub")
            self.disable_menus()
    
    def load_chapter_pos(self):
        self.provider.current_chapter = int(self.config.get(self.provider.book_md5, "chapter"))
        pos = float(self.config.get(self.provider.book_md5, "pos"))
        self.current_bookmark = pos
        # Kind of a hack
        self.check_current_bookmark_scroll = True
        self.bookmark_viewer_ready = True
        self.preload_book_scroll = self.scr_window.get_vadjustment().get_value()
        settings = self.viewer.get_settings()
        settings.props.user_stylesheet_uri = self.config.get(self.provider.book_md5, "stylesheet")
        
    def save_chapter_pos(self):
        if hasattr(self.provider,'book_md5'):
            self.config.set(self.provider.book_md5,"pos",self.scr_window.get_vadjustment().get_value())
            self.config.set(self.provider.book_md5, "chapter", self.provider.current_chapter)
            settings = self.viewer.get_settings()
            self.config.set(self.provider.book_md5, "stylesheet", settings.props.user_stylesheet_uri )
            
    def reload_chapter(self):
        if self.provider.ready:
            self.viewer.load_uri("file://"+self.provider.get_chapter_file(self.provider.current_chapter))

    def check_current_bookmark(self): #Scroll to bookmark if needed
        print "check_current_bookmark"
        if self.current_bookmark != 0 and self.check_current_bookmark_scroll and self.check_current_bookmark_viewer:
            print self.current_bookmark
            self.scr_window.get_vadjustment().set_value(self.current_bookmark)
            if self.scr_window.get_vadjustment().get_value()!=0.0 and self.scr_window.get_vadjustment().get_value() != self.preload_book_scroll: 
                self.current_bookmark = 0
                self.preload_book_scroll = -1;
                self.bookmark_scroll_ready = False
                self.bookmark_viewer_ready = False

    ##Signals
    def on_exit(self, widget, data=None): #Clean cache and exit
        settings = self.viewer.get_settings()
        self.save_chapter_pos()
        self.config.set("Main", "js", settings.props.enable_scripts)
        self.config.set("Main", "caret", settings.props.enable_caret_browsing)
        try:
            self.config.write(open(os.path.expanduser(os.path.join("~",".ppub.conf")), "wb"))
        except:
            error_dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, "Could not save configuration.")
            error_dialog.format_secondary_text("Make sure ~/.ppub.conf is accessible and writable and try again. Configuration from this session will be saved to /tmp/ppub.conf.")
            error_dialog.run()
            self.config.write(open("/tmp/ppub.conf", "wb"))
        cache_dir = self.config.get("Main", "cacheDir")
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
        Gtk.main_quit()

    def on_next_chapter(self, widget, data=None): #View next chapter
        #Note: Not directly loading the next chapter because the radio items
        #will update it on creation. Same applies for all
        #chapter changing actions
        self.provider.current_chapter = self.provider.current_chapter+1
        self.update_contents_menu()
        self.update_go_menu()

    def on_prev_chapter(self, widget, data=None): #View prev. chapter
        self.provider.current_chapter = self.provider.current_chapter-1
        self.update_contents_menu()
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

    def contents_menu_change(self, widget, data): #Change chapter according to selection
        if widget.get_active():
            self.provider.current_chapter = data
            self.viewer.load_uri("file://"+self.provider.get_chapter_file(data))

    def on_change_style(self, widget, data): #0=Def, 1=Night, 2=User
        settings = self.viewer.get_settings()
        if data == 0:
            settings.props.user_stylesheet_uri = ""
        elif data == 1:
            settings.props.user_stylesheet_uri = "file:///usr/share/ppub/night.css"
        else:
            settings.props.user_stylesheet_uri = "file://"+self.config.get("Main", "usercss")+"/"+widget.get_label()+".css"
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
        self.provider.current_chapter = chapter
        self.update_contents_menu()
        self.update_go_menu()

    def check_current_bookmark_scroll(self, widget, data=None):
        self.bookmark_scroll_ready = True
        self.check_current_bookmark()

    def check_current_bookmark_viewer(self, widget, data=None):
        self.bookmark_viewer_ready = True
        self.check_current_bookmark()

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
            if input_data <= self.provider.get_chapter_count():
                self.provider.current_chapter = input_data
                self.update_contents_menu()
                self.update_go_menu()
            else:
                error_dialog = Gtk.MessageDialog(self.window, 0, Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK, "Invalid chapter number.")
                error_dialog.format_secondary_text("Make sure the chapter you are asking for exists and try again.")
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

    def on_import(self, widget, data=None): #Show import dialog
        dialog = OpenDialog("Select book...", None, Gtk.FileChooserAction.OPEN,(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK), self.import_book, 1)
        dialog.run()

    def on_open(self, widget, data=None): #Show open dialog
        dialog = OpenDialog("Select book...", None, Gtk.FileChooserAction.OPEN, (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK), self.open_book, 0)
        dialog.run()

    def open_book(self, widget=None, data=None): #Open book (from dialog)
        filename = widget.get_filename()
        widget.destroy()
        self.save_chapter_pos()
        self.load_book(filename)

    def import_book(self, widget=None, data=None):
        filename = widget.get_filename()
        widget.destroy()
        spinnerDialog = SpinnerDialog()
        threading.Thread(target=self.bg_import_book, args=(filename,spinnerDialog)).start()
        spinnerDialog.run()

    def bg_import_book(self, filename, spinnerDialog):
        os.system("ebook-convert \""+filename+"\" /tmp/convert.epub --pretty-print")
        self.load_book("/tmp/convert.epub")
        spinnerDialog.destroy()

GObject.threads_init()
main = MainWindow()
Gtk.main()
