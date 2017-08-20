from threading import Thread, activeCount
from time import sleep
import json
import sys
import os

from tkFont import Font
from Tkinter import *
import tkSimpleDialog
import tkFileDialog
import ttk

import libs.t411api as tapi

sys.dont_write_bytecode = True

try:
    import libs.my_libtorrent as trnt
except ImportError:
    raise ImportError('The package: python-libtorrent is required.')

#
# CONFIG
#
initialDir = '~'

script_path = os.path.realpath(__file__)
script_dir = os.path.dirname(script_path)
configuration_path = os.path.join(script_dir, 'configuration.json')
try:
    with open(configuration_path) as configuration_file:
        configuration = json.load(configuration_file)
except:
    configuration = {}


#
# GUI
#
class TKTORRENTGUI(ttk.Frame):
    SortDir = True     # descending

    def __init__(self, name='hirudo'):
        ttk.Frame.__init__(self, name=name)
        self.pack(expand=Y, fill=BOTH)
        self.master.title('HIRUDO')
        self.torrentThreadList = {}
        self.isPopup = False
        if 'number_of_active_torrents' in configuration:
            self.active_torrents = configuration['number_of_active_torrents']
        else:
            self.active_torrents = 5
        if 'upload_limit' in configuration:
            self.upload_limit = configuration['upload_limit']
        else:
            self.upload_limit = 500000
        if 'download_limit' in configuration:
            self.download_limit = configuration['download_limit']
        else:
            self.download_limit = 9000000
        self.CreateWidgets()

    #
    # CreateWidgets
    #
    def CreateWidgets(self):
        # Bar
        menu = Menu(self)
        self.master.config(menu=menu)
        # File bar
        addBar = Menu(menu)
        menu.add_cascade(label='File', menu=addBar)
        addBar.add_command(label='Add File', command=self.AddFile)
        addBar.add_command(label='Add Folder', command=self.AddFolder)
        addBar.add_command(label='Maximum Number Of Active Torrents',
                           command=self.NumberOfActiveTorrents)
        addBar.add_command(label='Download Limit', command=self.DownloadLimit)
        addBar.add_command(label='Upload Limit', command=self.UploadLimit)
        addBar.add_command(label='Exit', command=self.Exit)
        # Torrent bar
        torrentBar = Menu(menu)
        menu.add_cascade(label='Torrent', menu=torrentBar)
        torrentBar.add_command(label='Start', command=self.CallStart)
        torrentBar.add_command(label='Stop', command=self.CallStop)
        torrentBar.add_command(label='Delete', command=self.Delete)
        # Search bar
        #  torrentBar = Menu(menu)
        #  menu.add_cascade(label='Search', menu=torrentBar)
        #  torrentBar.add_command(label='Keywords', command=self.SearchKeywords)
        # Torrent panel
        self.CreateTorrentPanel()

    #
    # Events
    #
    def RightClick(self, event):
        if self.isPopup:
            self.popupMenu.destroy()
            self.isPopup = False
        else:
            # Popup menu
            self.popupMenu = Menu(self, tearoff=0)
            self.popupMenu.add_command(label='Start', command=self.CallStart)
            self.popupMenu.add_command(label='Stop', command=self.CallStop)
            self.popupMenu.add_command(label='Delete', command=self.Delete)
            self.popupMenu.post(event.x_root, event.y_root)
            self.isPopup = True

    def ExitPopup(self, event):
        if self.isPopup:
            self.popupMenu.destroy()
            self.isPopup = False

    def SelectAll(self, event):
        for item in self.table.get_children():
            self.table.selection_add(item)

    #
    # CreateTorrentPanel
    #
    def CreateTorrentPanel(self):
        frame = Frame(self)
        frame.pack(side=TOP, fill=BOTH, expand=Y)
        # table
        self.torrentCols = ('Torrent', 'State')
        self.table = ttk.Treeview(columns=self.torrentCols, show='headings')
        # scrollbars
        ysb = ttk.Scrollbar(orient=VERTICAL, command=self.table.yview)
        xsb = ttk.Scrollbar(orient=HORIZONTAL, command=self.table.xview)
        self.table['yscroll'] = ysb.set
        self.table['xscroll'] = xsb.set
        # add table and scrollbars to frame
        self.table.grid(in_=frame, row=0, column=0, sticky=NSEW)
        ysb.grid(in_=frame, row=0, column=1, sticky=NS)
        xsb.grid(in_=frame, row=1, column=0, sticky=EW)
        # set frame resize priorities
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        # bind callback
        self.table.bind('<Double-1>',  self.CallStart)
        self.table.bind('<Button-3>',  self.RightClick)
        self.table.bind('<Button-1>',  self.ExitPopup)
        self.table.bind('<Escape>',    self.ExitPopup)
        self.table.bind('<Control-a>', self.SelectAll)
        # configure column headings
        for c in self.torrentCols:
            self.table.heading(c, text=c.title(),
                               command=lambda c=c:
                               self.ColumnSort(c, TKTORRENTGUI.SortDir))
            self.table.column(c, width=Font().measure(c.title()))

    #
    # ColumnSort
    #
    def ColumnSort(self, col, descending=False):
        # grab values
        data = [(self.table.set(child, col), child) for
                child in self.table.get_children('')]
        # reorder data
        data.sort(reverse=descending)
        for indx, item in enumerate(data):
            # item[1] = item Identifier
            self.table.move(item[1], '', indx)
        TKTORRENTGUI.SortDir = not descending

    #
    # LoadFile
    #
    def LoadFile(self, torrentFile):
        thread = trnt.TORRENTTHREAD(torrentFile)
        name = thread.GetTorrentName()
        if name not in self.torrentThreadList:
            self.torrentThreadList[name] = thread
        for item in self.table.get_children():
            if self.table.item(item)['text'] == name:
                return
        values = (name, 'NEW')
        self.table.insert('', 'end', text=name, values=values)
        for idx, val in enumerate(values):
            iwidth = Font().measure(val)
            if self.table.column(self.torrentCols[idx], 'width') < iwidth:
                self.table.column(self.torrentCols[idx], width=iwidth)

    #
    # AddFolder
    #
    def AddFolder(self):
        options = {}
        options['initialdir'] = initialDir
        options['mustexist'] = False
        options['parent'] = self
        options['title'] = 'DownDirectory'
        folder = tkFileDialog.askdirectory(**options)
        for file in os.listdir(folder):
            if file.endswith('.torrent'):
                torrentFile = os.path.join(folder, file)
                self.LoadFile(torrentFile)

    #
    # AddFile
    #
    def AddFile(self):
        options = {}
        options['initialdir'] = initialDir
        options['parent'] = self
        options['filetypes'] = [('Torrent file', '*.torrent')]
        file = tkFileDialog.askopenfilename(**options)
        folder = os.path.dirname(file)
        file = os.path.basename(file)
        if file.endswith('.torrent'):
            torrentFile = os.path.join(folder, file)
            self.LoadFile(torrentFile)

    #
    # NumberOfActiveTorrents
    #
    def NumberOfActiveTorrents(self):
        options = {}
        options['title'] = 'Number Of Active Torrents'
        options['prompt'] = 'Number Of Active Torrents'
        options['initialvalue'] = self.active_torrents
        options['parent'] = self
        options['minvalue'] = 0
        options['maxvalue'] = 50
        self.active_torrents = tkSimpleDialog.askinteger(**options)
        configuration['number_of_active_torrents'] = self.active_torrents
        with open(configuration_path, 'w') as configuration_file:
            json.dump(configuration, configuration_file,
                      indent=4, sort_keys=True)

    #
    # UploadLimit
    #
    def UploadLimit(self):
        options = {}
        options['title'] = 'Upload Limit'
        options['prompt'] = 'Upload Limit'
        options['initialvalue'] = self.upload_limit
        options['parent'] = self
        options['minvalue'] = 0
        options['maxvalue'] = 100000000000
        self.upload_limit = tkSimpleDialog.askinteger(**options)
        configuration['upload_limit'] = self.upload_limit
        with open(configuration_path, 'w') as configuration_file:
            json.dump(configuration, configuration_file,
                      indent=4, sort_keys=True)
        for name in self.torrentThreadList:
            if self.torrentThreadList[name].isAlive():
                self.torrentThreadList[name].SetUploadLimit(self.upload_limit)

    #
    # DownloadLimit
    #
    def DownloadLimit(self):
        options = {}
        options['title'] = 'Download Limit'
        options['prompt'] = 'Download Limit'
        options['initialvalue'] = self.download_limit
        options['parent'] = self
        options['minvalue'] = 0
        options['maxvalue'] = 100000000000
        self.download_limit = tkSimpleDialog.askinteger(**options)
        configuration['download_limit'] = self.download_limit
        with open(configuration_path, 'w') as configuration_file:
            json.dump(configuration, configuration_file,
                      indent=4, sort_keys=True)
        for name in self.torrentThreadList:
            if self.torrentThreadList[name].isAlive():
                self.torrentThreadList[name].SetDownloadLimit(self.download_limit)

    #
    # Choose among search results
    #
    def OnSearchSelection(self, response, api):
        torrents = []
        # Sort result by seeders and by size
        torrents = sorted(
            response['torrents'], key=lambda torrent: (
                int(torrent['seeders']),
                int(torrent['size'])),
            reverse=True)
        # Print result
        frame = Frame(self)
        frame.pack()
        listResults = Listbox(frame)
        # Print results
        for i, t in enumerate(torrents):
            listResults.insert(i, '%s (seeders: %s, size: %dmo, id: %s)' %
                               (t['name'], t['seeders'],
                                int(t['size'])/1000000, t['id']))

        def select(event):
            result = listResults.curselection()
            torrentFile = api.download(int(torrents[result[0]]['id']))
            self.LoadFile(torrentFile)
            frame.destroy()

        def clear():
            frame.destroy()
        btn = Button(frame, text='Cancel', command=clear)
        listResults.bind('<Double-Button-1>', select)
        listResults.bind('<Enter>', select)
        listResults.pack()
        btn.pack()

    #
    # Search Keywords
    #
    def SearchKeywords(self):
        options = {}
        options['parent'] = self
        torrent_name = tkSimpleDialog.askstring('Search keywords',
                                                'Example: Mad Max 2015',
                                                **options)
        api = tapi.T411API()
        api.connect(configuration["loginT411"], configuration["passwordT411"])
        response = api.search(torrent_name)
        self.OnSearchSelection(response, api)

    #
    # Exit
    #
    def Exit(self):
        for item in self.table.get_children():
            name = self.table.item(item)['text']
            if not name:
                continue
            if name in self.torrentThreadList:
                if self.torrentThreadList[name].isAlive():
                    self.torrentThreadList[name].Stop()
                self.torrentThreadList.pop(name, None)
            self.table.delete(item)
        self.quit()

    #
    # CallStart
    #
    def CallStart(self, event=None):
        for item in self.table.selection():
            if item:
                self.Start(item)

    #
    # Start
    #
    def Start(self, item):
        name = self.table.item(item)['text'].encode('utf8')
        if not name:
            return
        if activeCount() > MAX_THREADS:
            return
        if name in self.torrentThreadList and\
                not self.torrentThreadList[name].isAlive():
            torrentFile = self.torrentThreadList[name].torrentFile
            thread = trnt.TORRENTTHREAD(torrentFile)
            self.torrentThreadList.pop(name, None)
            self.torrentThreadList[name] = thread
            self.torrentThreadList[name].SetEditGui(self.Edit)
            self.torrentThreadList[name].SetItem(item)
            folder = os.path.dirname(os.path.realpath(torrentFile))
            self.torrentThreadList[name].SetOutput(folder)
            if 'user_passkey' in configuration and 'leech_passkey' in configuration:
                self.torrentThreadList[name].SetPasskey(configuration['user_passkey'],
                                                        configuration['leech_passkey'])
            self.torrentThreadList[name].SetDownloadLimit(self.download_limit)
            self.torrentThreadList[name].SetUploadLimit(self.upload_limit)
            self.torrentThreadList[name].start()

    #
    # CallStop
    #
    def CallStop(self):
        for item in self.table.selection():
            if item:
                self.Stop(item)

    #
    # Stop
    #
    def Stop(self, item):
        name = self.table.item(item)['text']
        if not name:
            return
        if name in self.torrentThreadList:
            if self.torrentThreadList[name].isAlive():
                self.torrentThreadList[name].Stop()

    #
    # Edit
    #
    def Edit(self, item, value):
        torrentName = self.table.item(item)['text'].replace('.torrent', '')
        self.table.item(item, values=(torrentName, value))

    #
    # Delete
    #
    def Delete(self):
        for item in self.table.selection():
            name = self.table.item(item)['text']
            if not name:
                return
            if name in self.torrentThreadList:
                if self.torrentThreadList[name].isAlive():
                    self.torrentThreadList[name].Stop()
                os.remove(self.torrentThreadList[name].torrentFile)
                self.torrentThreadList.pop(name, None)
            self.table.delete(item)


# Hide hidden elements
def hideHidden():
    root = Tk()
    try:
        # call a dummy dialog with an impossible option to initialize the file
        # dialog without really getting a dialog window; this will throw a
        # TclError, so we need a try...except :
        try:
            root.tk.call('tk_getOpenFile', '-foobarbaz')
        except TclError:
            pass
        # now set the magic variables accordingly
        root.tk.call('set', '::tk::dialog::file::showHiddenBtn', '1')
        root.tk.call('set', '::tk::dialog::file::showHiddenVar', '0')
    except:
        pass


#
# MAIN
#
if __name__ == '__main__':
    hideHidden()
    TKTORRENTGUI().mainloop()
