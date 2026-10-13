"""Manual smoke test of the learner path, without the learner.

Starts core + gNB + srsUE through the same scripts the learner uses, waits for the UE's
registration_request on the core's learner socket (60000), then sends the given symbols one by one
and prints each reply.  Usage (inside t1-enva, as root, from /work/learnrun):
    python3 probe.py auth_request_plain_text nas_sm_cmd registration_accept_protected
"""
import socket, subprocess, sys, time

def sh(cmd):
    subprocess.run(cmd, shell=True, check=False)

sh('./kill_evt.sh'); time.sleep(2)
sh('./start_core.sh'); time.sleep(4)
sh('./start_gnb.sh'); time.sleep(8)

# same handshake as UESUL.init_core_enb_con() and srsueSUL.Reset_Rach()
amf = socket.create_connection(('127.0.0.1', 60000)); amf_r = amf.makefile('r')
enb = socket.create_connection(('127.0.0.1', 60001)); enb_r = enb.makefile('r')
amf.settimeout(15); enb.settimeout(15)
time.sleep(2); amf.sendall(b'Hello\n'); print('core hello ->', amf_r.readline().strip())
time.sleep(2); enb.sendall(b'Hello\n'); print('gnb hello  ->', enb_r.readline().strip())
amf.sendall(b'RACH_Reset\n'); print('core RACH_Reset ->', amf_r.readline().strip())
enb.sendall(b'RACH_Reset\n'); print('gnb RACH_Reset  ->', enb_r.readline().strip())

try:
    sh('./start_ue.sh')
    print('enable_s1 ->', amf_r.readline().strip())

    amf.settimeout(3)
    for sym in sys.argv[1:]:
        time.sleep(0.5)
        amf.sendall((sym + '\n').encode())
        try:
            reply = amf_r.readline().strip()
        except socket.timeout:
            reply = '(timeout)'
        print(sym, '->', reply)
finally:
    # like srsueSUL.pre(): close our side first, so the gNB's port 60001 is not left in TIME_WAIT
    amf.close(); enb.close(); time.sleep(1)
    sh('./kill_evt.sh')
