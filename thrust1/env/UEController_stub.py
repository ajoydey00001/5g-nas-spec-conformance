# Stub UE controller for srsUE. Upstream drives Android phones over adb; srsueSUL starts/kills srsUE itself
# through start_ue.sh / kill_evt.sh, and only needs this socket to exist and answer DONE.
import socket, threading
def serve(c):
    f = c.makefile('r')
    for line in f:
        c.sendall(b'DONE\n')
s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('127.0.0.1', 61000)); s.listen(5)
while True:
    c, _ = s.accept(); threading.Thread(target=serve, args=(c,), daemon=True).start()
