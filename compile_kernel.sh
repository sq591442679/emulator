cd /home/sqsq/Desktop/linux-5.15.132-sqsq
echo ""
sudo make -j$(nproc) 2>&1 | grep -E 'error:|warning:'
sudo make -j$(nproc) INSTALL_MOD_STRIP=1 modules_install 2>&1 | grep -E 'error:|warning:'
sudo make install 2>&1 | grep -E 'error:|warning:'  # only print warning and errors on terminal
sudo update-grub > /dev/null
# sudo make clean > /dev/null
