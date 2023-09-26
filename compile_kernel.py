import os

script_path = '/home/sqsq/Desktop/emulator/compile_kernel.sh'
sudo_password = 'shanqian'

sudo_command = f"echo '{sudo_password}' | sudo -S '{script_path}'"

if __name__ == '__main__':
    os.system(sudo_command)
