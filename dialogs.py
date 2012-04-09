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

from gi.repository import Gdk, Gtk

class OpenDialog(Gtk.FileChooserDialog): #File>Open dialog
    def __init__(self, title, none, action, buttons, activate, files):
        super(OpenDialog, self).__init__(title, none, action, buttons)
        #Prepare filters
        if files == 0: #For open dialog only
            filter_pub = Gtk.FileFilter()
            filter_pub.set_name("EPub files")
            filter_pub.add_pattern("*.epub")
            self.add_filter(filter_pub)
        #For all dialogs
        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")
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
        #Set window properties
        self.set_resizable(False)
        #Create widgets
        label = Gtk.Label("Enter chapter number:") #Label
        self.entry = Gtk.Entry() #Textbox
        #Actions
        self.entry.connect("activate", self.on_dialog_enter) #Close on enter
        #Add to container
        self.vbox.pack_start(self.entry, True, True, 0)
        self.vbox.pack_start(label, True, True, 0)
        self.vbox.show_all()
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

class SpinnerDialog(Gtk.Dialog): #Convert book spinner
    def __init__(self):
        super(SpinnerDialog, self).__init__()
        #Window options
        self.set_resizable(False)
        #Create container and objects
        hbox = Gtk.HBox()
        spinner = Gtk.Spinner()
        label = Gtk.Label("Importing...")
        #Start spinner and set size
        spinner.start()
        spinner.set_size_request(50,50)
        #Add objects to containers
        hbox.pack_start(spinner, True, True, 10)
        hbox.pack_start(label, True, True, 10)
        self.vbox.pack_start(hbox, True, True, 0)
        self.vbox.show_all()

class DeleteBookmarksDialog(Gtk.Dialog):
    def __init__(self, config, book_md5, action):
        #Window properties
        super(DeleteBookmarksDialog, self).__init__()
        self.set_title("Bookmarks")
        self.set_size_request(350, 250)
        self.activation_action = action
        #Variables
        self.config = config
        self.book_md5 = book_md5
        #Create objects
        label = Gtk.Label("Double click a bookmark to delete.") #Label
        self.scr_window = Gtk.ScrolledWindow() #Scrollable Area
        #Set properties of Scrollable Area
        self.scr_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scr_window.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        #Add objects to container
        self.vbox.pack_end(self.scr_window, True, True, 0)
        self.vbox.pack_start(label, False, False, 0)
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
        #Re-add widget
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
