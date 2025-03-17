if [ ! -f .already ]; then
  touch .already

  if command -v apt > /dev/null; then
    echo "export PATH=$PATH:~/.local/bin/" >> ~/.bashrc
    sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev android-tools-adb
  fi

  if command -v pacman > /dev/null; then
    sudo pacman -S --noconfirm zip cmake python3 python3-pip base-devel cython autoconf openjdk-17-jdk libtool pkg-config zlib ncurses libffi openssl unzip
    if command -v paru > /dev/null; then
      paru -S --noconfirm android-sdk-platform-tools
    elif command -v yay > /dev/null; then
      yay -S --noconfirm android-sdk-platform-tools
    fi
  fi

  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  pip install -r kahiin/requirements.txt
  source ~/.bashrc
  git submodule update --init --recursive
fi

git submodule update --remote --merge
source venv/bin/activate
python main.py