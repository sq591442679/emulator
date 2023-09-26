cd /home/sqsq/Desktop/linux-5.15.132
sudo make -j$(nproc)
sudo make -j$(nproc) INSTALL_MOD_STRIP=1 modules_install
sudo make install
sudo update-grub