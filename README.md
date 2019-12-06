A cross-platform (Mac, Win, Linux) clipboard synchronization tool. It's
abandoned as I don't need this anymore, but I'm posting the code online in case
it's useful to anyone.

What it does:
- Synchronizes system clipboard across devices
- Supports synchronizing either over local network or Internet server.
- Works with images, pops up a progress indicator for file transfers.
- System tray indicator shows if the clipboard is synced, disconnected, or if
  a new paste was copied from another system recently.

What's missing:
- A tiny bit of UI polish
- Packaging / running instructions, though setup.py deps and installer are working fine.
- Local network discovery
- Security


There's some key features missing. However, the parts that are working work
well, for me. I've used the clipboard syncing a lot and had time to work out the
kinks.


#### Acknowledgements

Icons were designed by Freepik from FlatIcon.
