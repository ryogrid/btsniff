#!/usr/bin/env python

import os
import sys
import time
from base64 import b32encode
from os import path

sys.path.append(path.dirname("/usr/lib/python2.7/dist-packages/"))

#import ctypes
#lib = ctypes.cdll.LoadLibrary(PATH_TO_LIB)

import libtorrent as lt

class Btsniff:
    def __init__(self):
        self.ses = None
        self.serial = 0L
        self.info_hashes = {}

    def start(self, torrent_file, port=6881):
        if not os.path.isdir('log'):
            os.mkdir('log')

        print("libtorrent version: " + lt.version)
        self.ses = lt.session()
        self.ses.set_alert_mask(lt.alert.category_t.status_notification | 0x400) # lt.alert.category_t.dht_notification
        #self.ses.set_alert_mask(lt.alert.category_t.dht_notification)
        #self.ses.set_alert_mask(lt.alert.category_t.all_categories)
        # returned None
        #peer_id = self.ses.listen_on(port, port)
        #print(str(peer_id))
        
        self.ses.start_dht()
        self.ses.add_dht_router("router.bittorrent.com", 6881)
        self.ses.add_dht_router("router.utorrent.com", 6881)
        self.ses.add_dht_router("router.bitcomet.com", 6881)

        dstate = self.ses.dht_state()
        # print peer ID
        print(dstate)

        
        info = lt.torrent_info(torrent_file)
        h = self.ses.add_torrent({'ti': info, 'save_path': './'})
        
        s = h.status()
        print('starting', s.name)
        
        while not h.is_seed():
            alert = self.ses.pop_alert()
            while alert is not None:
                #if self.serial % 30 == 0:
                #    s = h.status()
                #    print(s.name)
                #    print('%s: \r%.2f%% complete (down: %.1f kB/s up: %.1f kB/s peers: %d) %s' % (
                #        s.name, s.progress * 100, s.download_rate / 1000, s.upload_rate / 1000,
                #        s.num_peers, s.state))
                self.handle_alert(alert)
                alert = self.ses.pop_alert()
            time.sleep(0.1)

        self.ses.remove_torrent(h)

        while True:
            alert = self.ses.pop_alert()
            while alert is not None:
                self.handle_alert(alert)
                alert = self.ses.pop_alert()
            time.sleep(0.1)

    def handle_alert(self, alert):
        alert_type = type(alert).__name__
        print "[%s] %s" % (alert_type, alert.message())

        # only empty string printed
        # torrent_list = self.ses.get_torrents()
        # for tr_handle in torrent_list:
        #     print(tr_handle.status().name)
        if alert_type == 'dht_get_peers_alert':
            print "[%s] %s" % (alert_type, alert.message())
            try:
                info_hash = alert.info_hash.to_string()
            except:
                return

            #rkan added
            #print(info_hash)

            # this code return only on my own information.... 
            #tr_handle = self.ses.find_torrent(alert.info_hash)
            #tr_info = tr_handle.torrent_file()
            #print(str(tr_info))
            
            self.serial += 1
            if not info_hash in self.info_hashes:
                self.info_hashes[info_hash] = {'serial': self.serial, 'unixtime': time.time()}
            else:
                return

            h = self.ses.add_torrent({'info_hash': alert.info_hash.to_bytes(), 'save_path': './'})
            #s = h.status()
            #print('added torrent via get_peers_alert', str(s.state))
            h.queue_position_top()
        elif alert_type == 'metadata_received_alert':
            print "[%s] %s" % (alert_type, alert.message())
            h = alert.handle
            info_hash = str(h.info_hash())
            if h.is_valid():
                ti = h.get_torrent_info()
                serial = self.info_hashes[info_hash]['serial']
                unixtime = self.info_hashes[info_hash]['unixtime']
                line = '\t'.join([
                        str(serial),
                        time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(unixtime)), 
                        info_hash, 
                        str(ti.total_size()), 
                        str(ti.num_files()), 
                        ti.name(), 
                        ti.comment(), 
                        ti.creator(), 
                ])
                fpath = time.strftime('log/btsniff-%Y%m%d.log', time.localtime(unixtime))
                with open(fpath, 'a') as f:
                    print >>f, line
                    f.flush()
                self.ses.remove_torrent(h, 1) # session::delete_files
        elif alert_type == 'torrent_added_alert':
            print "[%s] %s" % (alert_type, alert.message())
            # try:
            #     info_hash = alert.info_hash.to_string()
            # except:
            #     return
            
            # self.serial += 1
            # if not info_hash in self.info_hashes:
            #     self.info_hashes[info_hash] = {'serial': self.serial, 'unixtime': time.time()}
            # else:
            #     return

            # h = self.ses.add_torrent({'info_hash': alert.info_hash.to_bytes(), 'save_path': './'})
            # h.queue_position_top()
        elif alert_type == 'add_torrent_alert':
            print "[%s] %s" % (alert_type, alert.message())
            # try:
            #     info_hash = alert.info_hash.to_string()
            # except:
            #     return
            
            # self.serial += 1
            # if not info_hash in self.info_hashes:
            #     self.info_hashes[info_hash] = {'serial': self.serial, 'unixtime': time.time()}
            # else:
            #     return

            # h = self.ses.add_torrent({'info_hash': alert.info_hash.to_bytes(), 'save_path': './'})
            # h.queue_position_top()

 


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print >>sys.stderr, "Usage: python %s TORRENT_FILE" % sys.argv[0]
        sys.exit(1)
    torrent_file = sys.argv[1]

    btsniff = Btsniff()
    btsniff.start(torrent_file)
