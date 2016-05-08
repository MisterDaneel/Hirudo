#!/usr/bin/env python
#
# A simple torrent client application
# from https://github.com/MisterDaneel/
#
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
import libtorrent as lt
import time
import sys
import os
import Tkinter as tk
import ttk
import tkFileDialog
#import threading
from threading import Thread

MAX_THREADS = 5
#
# CONFIG
#
state_str            = ['queued', 'checking', 'downloading metadata', 'downloading', 'finished', 'seeding', 'allocating', 'checking fastresume']
undesirableTracker   = ''
newTracker           = ''
initialDir           = '~/Downloads'
UploadLimit          = 9000000
DownloadLimit        = 9000000
#
# TORRENTBOX GUI
#
class TORRENTBOX_GUI(tk.Frame):
   def __init__(self, torrentBox):
      tk.Frame.__init__(self, torrentBox)
      self.torrentBox = torrentBox
      self.button_opt = {'fill': 'both', 'padx': 5, 'pady': 5}
      self.torrentNameGUI = ttk.Label(self)
      self.torrentNameGUI.pack(**self.button_opt)
   def InitTB(self, torrentName):
      self.torrentNameGUI["text"] = torrentName + '\nINITIALISATION'
   def Checking(self, torrentName, progress, state):
      infosSTR = '%.2f%% %s' % (progress * 100, state_str[state])
      self.torrentNameGUI["text"] = torrentName + '\n' + infosSTR
      sys.stdout.flush()
   def Downloading(self, torrentName, progress, state, num_peers, download_rate, upload_rate):
      infosSTR = '%.2f%% (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % (progress * 100, download_rate / 1000, upload_rate / 1000, num_peers, state_str[state])
      self.torrentNameGUI["text"] = torrentName + '\n' + infosSTR
      sys.stdout.flush()
   def Complete(self, torrentName):
      self.torrentNameGUI["text"] = torrentName + '\nCOMPLETE'
      print torrentName, 'COMPLETE'
#
# TORRENT THREAD
#
class TORRENTTHREAD(Thread):
   def __init__(self, folder, file, rootBox):
      super(TORRENTTHREAD, self).__init__()
      self.torrentBox = TORRENTBOX_GUI(rootBox)
      self.torrentBox.pack(fill='both', expand=1)
      file = file.decode(sys.getfilesystemencoding())
      print 'Thread file =', file
      print 'Thread folder =', folder
      self.info = lt.torrent_info(os.path.join(folder, file))
      self.folder = folder
   def run(self):
      # New Session
      ses = lt.session()
      ses.listen_on(6881, 6891)
      self.torrentHandle = ses.add_torrent({'ti': self.info, 'save_path': self.folder})
      self.torrentHandle.set_download_limit(1)
      self.torrentHandle.set_upload_limit(UploadLimit)
      # New Torrent
      torrentName = self.torrentHandle.name()
      self.torrentBox.InitTB(torrentName)
      #Peering
      if((self.torrentHandle.status().num_peers < 1) and not self.torrentHandle.is_seed()):
         self.Peering()
      #newTrackers
      newTrackers = []
      for tr in self.torrentHandle.trackers():
         for undesirableTracker in tr['url']:
            tr['url'] = newTracker
         newTrackers.append(tr)
      self.torrentHandle.replace_trackers(newTrackers)
      for tracker in self.torrentHandle.trackers():
         print '\rTracker: ', tracker['url']
      #Downloading
      if(not self.torrentHandle.is_seed()):
         self.Downloading()
      #Complete
      self.torrentBox.Complete(torrentName)

   def isComplete(self):
      return self.torrentHandle.is_seed()
   def destroy(self):
      self.torrentBox.destroy()
   def Peering(self):
      torrentStatus = self.torrentHandle.status()
      while ((torrentStatus.num_peers < 1) and not self.torrentHandle.is_seed()):
         if (torrentStatus.state == 1):
            self.torrentBox.Checking(self.torrentHandle.name(), torrentStatus.progress, torrentStatus.state)
         time.sleep(.1)
         torrentStatus = self.torrentHandle.status()
         
   def Downloading(self):
      self.torrentHandle.set_download_limit(DownloadLimit)
      torrentStatus = self.torrentHandle.status()
      while (not self.torrentHandle.is_seed()):
         if (torrentStatus.state == 1):
            self.torrentBox.Checking(self.torrentHandle.name(), torrentStatus.progress, torrentStatus.state)
         else:
            self.torrentBox.Downloading(self.torrentHandle.name(), torrentStatus.progress, torrentStatus.state, torrentStatus.num_peers, torrentStatus.download_rate, torrentStatus.upload_rate)
         time.sleep(.1)
         torrentStatus = self.torrentHandle.status()
#
# TORRENT CLIENT
#
class TORRENTCLIENT_GUI(tk.Frame):
   def __init__(self, root):
      tk.Frame.__init__(self, root)
      self.root = root
      self.InitGUI()
   def InitGUI(self):
      # Title
      self.root.title("TORRENT CLIENT")
      self.pack(fill='both', expand=1)
      # Menu
      self.menubar = tk.Menu(self.root)
      self.root.config(menu=self.menubar)
      self.menubar.add_command(label="Add Folder", command=self.AddFolder)
      self.menubar.add_command(label="Add File", command=self.AddFile)
      # List
      scrollbarY = tk.Scrollbar(self.root)
      scrollbarY.pack(side='right', fill='y')
      self.listBox = tk.Listbox(self.root)
      self.listBox.pack(fill='both', expand=1)
      self.listBox.config(yscrollcommand=scrollbarY.set)
      self.listBox.bind('<<ListboxSelect>>', self.Select)
      scrollbarY.config(command=self.listBox.yview)
      self.listTorrent = {}
   def AddFolder(self):
      options = {}
      options['initialdir'] = initialDir
      options['mustexist'] = False
      options['parent'] = root
      options['title'] = 'DownDirectory'
      folder = tkFileDialog.askdirectory(**options)
      for file in os.listdir(folder):
         if file.endswith(".torrent") and file not in self.listTorrent:
            self.listTorrent[file] = [folder, True, None]
            self.listBox.insert(tk.END, file)
   def AddFile(self):
      options = {}
      options['initialdir'] = initialDir
      options['parent'] = root
      file = tkFileDialog.askopenfilename(**options)
      folder = os.path.dirname(file)
      file = os.path.basename(file)
      if file.endswith(".torrent") and file not in self.listTorrent:
         self.listTorrent[file] = [folder, True, None]
         self.listBox.insert(tk.END, file)

   def ClearC(self):
      for file in self.listTorrent:
         [folder, toThread, tt] = self.listTorrent[file]
         if not toThread and tt.isComplete():
               tt.destroy()

   def Select(self, event):
         w = event.widget
         index = int(w.curselection()[0])
         file = w.get(index)
         [folder, toThread, tt] = self.listTorrent[file]
         if toThread: #and threading.activeCount() < MAX_THREADS:
            tt = TORRENTTHREAD(folder, file, self)
            tt.start()
            self.listTorrent[file] = [folder, False, tt]
         else:
            print tt.isComplete()
#
# MAIN
#
if __name__=='__main__':
   root = tk.Tk()
   TORRENTCLIENT_GUI(root).pack()
   root.mainloop()
