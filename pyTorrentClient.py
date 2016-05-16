#!/usr/bin/env python
#
# A simple torrent client application
# from https://github.com/MisterDaneel/
#
# sudo apt-get install python-libtorrent
# sudo apt-get install python-tk
#
# Copyright (C) {2016}  {MisterDaneel}
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
from threading import Thread, activeCount
from tkFont import Font
from Tkinter import *
import tkFileDialog
import ttk
import libtorrent as lt
from time import sleep
import os
import Queue
#
# CONFIG
#
MAX_THREADS          = 5
undesirableTracker   = ''
newTracker           = ''
initialDir           = '~/Downloads'
UploadLimit          = 100000
DownloadLimit        = 9000000
state_str            = ['queued', 'checking', 'downloading metadata', 'downloading', 'finished', 'seeding', 'allocating', 'checking fastresume']
#
# TORRENT THREAD
#
class TORRENTTHREAD(Thread):
    toStop = False
    def __init__(self, folder, file, item, EditGui):
        super(TORRENTTHREAD, self).__init__()
        self.EditGui = EditGui
        self.item = item
        #file = file.decode(sys.getfilesystemencoding())
        print 'New Torrent =', file
        print 'Folder =', folder
        self.info = lt.torrent_info(os.path.join(folder, file))
        self.folder = folder
    #
    # Start
    #
    def run(self):
        # New Session
        ses = lt.session()
        ses.listen_on(6881, 6891)
        self.torrentHandle = ses.add_torrent({'ti': self.info, 'save_path': self.folder})
        self.torrentHandle.set_download_limit(1)
        self.torrentHandle.set_upload_limit(UploadLimit)
        # New Torrent
        torrentName = self.torrentHandle.name()
        self.EditGui(self.item, 'INITIALISATION')
        # Peering
        print self.torrentHandle.name() + ' Peering'
        if((self.torrentHandle.status().num_peers < 1) and not self.torrentHandle.is_seed()):
            self.Peering()
        if self.toStop:
            return
        # New Tracker
        newTrackers = []
        for tr in self.torrentHandle.trackers():
            for undesirableTracker in tr['url']:
                tr['url'] = newTracker
            newTrackers.append(tr)
        self.torrentHandle.replace_trackers(newTrackers)
        for tracker in self.torrentHandle.trackers():
            print '\rTracker: ', tracker['url']
        # Downloading
        print self.torrentHandle.name() + ' Downloading'
        if(not self.torrentHandle.is_seed()):
            self.Downloading()
        if self.toStop:
            return
        # Complete
        self.EditGui(self.item, 'COMPLETED')
    #
    # Peering
    #
    def Peering(self):
        torrentStatus = self.torrentHandle.status()
        while (not self.toStop and (torrentStatus.num_peers < 1) and not self.torrentHandle.is_seed()):
            if (torrentStatus.state == 1):
                infosSTR = '%.2f%% %s' % (torrentStatus.progress * 100, state_str[torrentStatus.state])
                self.EditGui(self.item, infosSTR)
            sleep(.1)
            torrentStatus = self.torrentHandle.status()
    #
    # Downloading
    #
    def Downloading(self):
        self.torrentHandle.set_download_limit(DownloadLimit)
        torrentStatus = self.torrentHandle.status()
        while (not self.toStop and not self.torrentHandle.is_seed()):
            if (torrentStatus.state == 1):
                infosSTR = '%.2f%% %s' % (torrentStatus.progress * 100, state_str[torrentStatus.state])
                self.EditGui(self.item, infosSTR)
            else:
                infosSTR = '%.2f%% (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % (torrentStatus.progress * 100, torrentStatus.download_rate / 1000, torrentStatus.upload_rate / 1000, torrentStatus.num_peers, state_str[torrentStatus.state])
                self.EditGui(self.item, infosSTR)
            sleep(.1)
            torrentStatus = self.torrentHandle.status()
    #
    # Stop
    #
    def Stop(self):
        self.toStop = True
        self.EditGui(self.item, 'STOPPED')
        return
#
# GUI
#
class TKTORRENTGUI(ttk.Frame):
    SortDir = True     # descending
    def __init__(self, name='tktorrent'):
        ttk.Frame.__init__(self, name=name)
        self.pack(expand=Y, fill=BOTH)
        self.master.title('TK TORRENT')
        self.torrentThreadList = {}
        self.torrentFolderList = {}
        self.isPopup = False
        self.CreateWidgets()
    #
    # CreateWidgets
    #
    def CreateWidgets(self):
        # bar
        menu = Menu(self)
        self.master.config(menu=menu)
        # File bar
        addBar = Menu(menu)
        menu.add_cascade(label='File', menu=addBar)
        addBar.add_command(label='Add File', command=self.AddFile)
        addBar.add_command(label='Add Folder', command=self.AddFolder)
        addBar.add_command(label='Exit', command=self.Exit)
        # Torrent bar
        torrentBar = Menu(menu)
        menu.add_cascade(label='Torrent', menu=torrentBar)
        torrentBar.add_command(label='Start', command=self.CallStart)
        torrentBar.add_command(label='Stop', command=self.CallStop)
        torrentBar.add_command(label='Delete', command=self.Delete)
        # Torrent panel
        torrentPanel = Frame(self)
        torrentPanel.pack(side=TOP, fill=BOTH, expand=Y)
        self.CreateTorrentPanel(torrentPanel)
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
    def CreateTorrentPanel(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(side=TOP, fill=BOTH, expand=Y)
        # table
        self.torrentCols = ('Torrent', 'State')        
        self.table = ttk.Treeview(columns=self.torrentCols, show = 'headings')
        # scrollbars
        ysb = ttk.Scrollbar(orient=VERTICAL, command= self.table.yview)
        xsb = ttk.Scrollbar(orient=HORIZONTAL, command= self.table.xview)
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
            self.table.heading(c, text=c.title(), command=lambda c=c: self.ColumnSort(c, TKTORRENTGUI.SortDir))            
            self.table.column(c, width=Font().measure(c.title()))
    #
    # ColumnSort
    #
    def ColumnSort(self, col, descending=False):
        # grab values
        data = [(self.table.set(child, col), child) for child in self.table.get_children('')]
        # reorder data
        data.sort(reverse=descending)
        for indx, item in enumerate(data):
            # item[1] = item Identifier
            self.table.move(item[1], '', indx)
        TKTORRENTGUI.SortDir = not descending
    #
    # LoadFile
    #
    def LoadFile(self, file, folder):
        for item in self.table.get_children():
            if self.table.item(item)['text'] == file:
                return
        values = (file.replace('.torrent', ''), 'NEW')
        self.table.insert('', 'end', text=file, values=values)
        self.torrentFolderList[file] = folder
        for idx, val in enumerate(values):
            iwidth = Font().measure(val)
            if self.table.column(self.torrentCols[idx], 'width') < iwidth:
                self.table.column(self.torrentCols[idx], width = iwidth)
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
            if file.endswith('.torrent') and file not in self.torrentFolderList:
                self.LoadFile(file, folder)
    #
    # AddFile
    #
    def AddFile(self):
        options = {}
        options['initialdir'] = initialDir
        options['parent'] = self
        file = tkFileDialog.askopenfilename(**options)
        folder = os.path.dirname(file)
        file = os.path.basename(file)
        if file.endswith('.torrent') and file not in self.torrentFolderList:
            self.LoadFile(file, folder)
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
            if name in self.torrentFolderList:
                self.torrentFolderList.pop(name, None)
        self.quit()
    #
    # CallStart
    #
    def CallStart(self, event = None):
        for item in self.table.selection():
            if item:
                self.Start(item)
    #
    # Start
    #
    def Start(self, item):
        name = self.table.item(item)['text']
        if not name:
            return
        if activeCount() > MAX_THREADS:
            return
        if name not in self.torrentThreadList:
            self.queue = Queue.Queue()
            thread = TORRENTTHREAD(self.torrentFolderList[name], self.table.item(item)['text'], item, self.Edit)
            thread.start()
            self.torrentThreadList[name] = thread
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
            self.torrentThreadList.pop(name, None)
    #
    # Edit
    #
    def Edit(self, item, value):
        file = self.table.item(item)['text']
        self.table.item(item, values=(file, value))
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
                self.torrentThreadList.pop(name, None)
            self.table.delete(item)
            if name in self.torrentFolderList:
                self.torrentFolderList.pop(name, None)
#
# MAIN
#
if __name__ == '__main__':
    TKTORRENTGUI().mainloop()
