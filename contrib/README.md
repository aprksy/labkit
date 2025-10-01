# incuslab

> 🔧 Event-driven automation for [Incus](https://github.com/lxc/incus) containers and VMs.

`incuslab` listens to Incus events (like `container-started`) and triggers actions such as updating SSH configs or `/etc/hosts`.

Perfect for homelab automation and developer workflows.

## Features

- 🎯 Reacts to lifecycle events
- 🔌 Pluggable architecture
- 🔐 Configurable via `.env`
- 📦 Easy to extend


## Quick Start

```bash
git clone https://github.com/aprksy/incuslab.git
cd incuslab
cp .env.example .env
nano .env  # edit values
pip install python-dotenv
python main.py
```

Enable as service: 
```bash
sudo cp systemd/incuslab.service /etc/systemd/system/incuslab@youruser.service
sudo systemctl enable --now incuslab@youruser
```
 
Plugins Included 
- `ssh_config.py`: Auto-generates SSH config
- `regen_ssh_host_keys.py`: Auto generate SSH Host key for newly created container on the first boot
- `shared_storage.py`: Auto mount shared dir on the host to `/shared` dir on the container

Utilities
- `incus-clone`: A wrapper for `incus copy` command to automatically unset the `firstboot` metadata.

Template Included
- `template_example.py`: How to write new plugins
- `template_systemd.service`: How to write systemd service for your system
     

## License 

MIT 