# VK Social Graph

[Social graph](https://en.wikipedia.org/wiki/Social_graph) is a model, where each person is represented as node (dot/circle) and relations between people are represented as lines.

This software generates a social graph of any vk.com user and exports it to SVG plot.

## Installation

Arch Linux:

```bash
sudo pacman -S python-{requests,pip} git
git clone https://github.com/MikeWent/vk-social-graph.git
cd vk-social-graph/
pip3 install --user wheel
pip3 install --user -r requirements.txt
```

## License

GPLv3
