#!/usr/bin/env python
#
# A simple torrent client application
# from https://github.com/MisterDaneel/
#
# sudo apt-get install python-libtorrent
# sudo apt-get install python-tk
#
import libtorrent as lt
import time
import sys
import os
import Tkinter as tk
import ttk
import tkFileDialog
import Tkconstants
#
# CONFIG
#
state_str            = ['queued', 'checking', 'downloading metadata', 'downloading', 'finished', 'seeding', 'allocating', 'checking fastresume']
undesirableTracker   = ''
newTracker           = ''
initialDir           = '~/Downloads'
UploadLimit          = 10000000
DownloadLimit        = 10000000

class TORRENTCLIENT_IHM(tk.Frame):
   def __init__(self, root):
      tk.Frame.__init__(self, root)
      self.button_opt = {'fill': Tkconstants.BOTH, 'padx': 5, 'pady': 5}
      self.START = tk.Button(self, text='CHOOSE DIRECTORY', command=self.downloadDirectory)
      self.START.pack(**self.button_opt)
      self.dir_opt = options = {}
      options['initialdir'] = initialDir
      options['mustexist'] = False
      options['parent'] = root
      options['title'] = 'DownDirectory'
   
   def downloadDirectory(self):
      folder = tkFileDialog.askdirectory(**self.dir_opt) + '/'
      ses = lt.session()
      ses.listen_on(6881, 6891)
      print 'listen_on(6881, 6891)'
      self.START.destroy()
      torrentNameIHM = ttk.Label(self, text='TORRENT')
      torrentProgressIHM = ttk.Progressbar(self, orient='horizontal', mode='determinate')
      torrentInfoIHM = ttk.Label(self, text="INITIALISATION")
      torrentConsoleIHM = tk.Text(self)
      torrentNameIHM.pack(**self.button_opt)
      torrentProgressIHM.pack(**self.button_opt)
      torrentInfoIHM.pack(**self.button_opt)
      torrentConsoleIHM.pack(**self.button_opt)
      for file in os.listdir(folder):
         if file.endswith(".torrent"):
            print '**************************'
            file = file.decode(sys.getfilesystemencoding())
            info = lt.torrent_info(folder + file)
            # Torrent
            torrentHandle = ses.add_torrent({'ti': info, 'save_path': folder})
            torrentHandle.set_download_limit(1)
            torrentHandle.set_upload_limit(UploadLimit)
            torrentStatus = torrentHandle.status()
            # IHM
            torrentNameIHM["text"] = torrentHandle.name()
            torrentProgressIHM.start()
            torrentProgressIHM["maximum"] = 101
            torrentProgressIHM["value"] = 0
            torrentInfoIHM["text"] = "INITIALISATION"
            torrentProgressIHM.update()
            #
            # Peering
            #
            timeCount = 0
            while ((torrentStatus.num_peers < 1) and (timeCount < 5) and not torrentHandle.is_seed()):
               torrentStatus = torrentHandle.status()
               print '\rpeers: %d time: %d s' % (torrentStatus.num_peers, timeCount),
               sys.stdout.flush()
               time.sleep(1)
               timeCount += 1
            #
            # Change tracker
            #
            newTrackers = []
            for tr in torrentHandle.trackers():
               for undesirableTracker in tr['url']:
                  tr['url'] = newTracker
               newTrackers.append(tr)
            torrentHandle.replace_trackers(newTrackers)
            for tracker in torrentHandle.trackers():
               print '\rTracker: ', tracker['url']
            #
            # Downloading
            #
            torrentHandle.set_download_limit(DownloadLimit)
            torrentConsoleIHM.insert(tk.END, 'Downloading '+file+'\n')
            while (not torrentHandle.is_seed()):
               torrentStatus = torrentHandle.status()
               torrentProgressIHM["value"] = torrentStatus.progress * 100
               torrentProgressIHM.update()
               if (torrentStatus.state == 1):
                  infosSTR = '%.2f%% %s' % (torrentStatus.progress * 100, state_str[torrentStatus.state])
               else:
                  infosSTR = '%.2f%% (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % (torrentStatus.progress * 100, torrentStatus.download_rate / 1000, torrentStatus.upload_rate / 1000, torrentStatus.num_peers, state_str[torrentStatus.state])
               torrentInfoIHM["text"] = infosSTR
               print '\r' + infosSTR,
               sys.stdout.flush()
               time.sleep(1)
            torrentStatus = torrentHandle.status()
            #progress.destroy()
            #torrentInfoIHM.destroy()
            torrentInfoIHM["text"] = 'COMPLETE'
            torrentConsoleIHM.insert(tk.END, torrentHandle.name()+' COMPLETE\n*****\n')
            print torrentHandle.name(), 'COMPLETE'
            
#
# MAIN
#
if __name__=='__main__':
   root = tk.Tk()
   TORRENTCLIENT_IHM(root).pack()
   root.wm_title("TORRENTCLIENT")
   root.mainloop()
