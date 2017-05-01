sudo apt-get update
sudo apt-get install -y automake wget libboost-all-dev libssl-dev g++ make python python-libtorrent
wget https://downloads.sourceforge.net/project/libtorrent/libtorrent/libtorrent-rasterbar-1.0.5.tar.gz
tar -zxvf libtorrent-rasterbar-1.0.5.tar.gz
rm libtorrent-rasterbar-1.0.5.tar.gz
cd libtorrent-rasterbar-1.0.5
./configure --enable-python-binding && \
make && \
sudo make install
cd ..
