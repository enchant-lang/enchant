"""Real credits, OS backpressure, private completion and descendant custody."""
import fcntl
import json
import os
from pathlib import Path
import select
import signal
import struct
import subprocess
import tempfile
import time
from unittest.mock import patch
import test_command_domain as custody


class CommandStreamControls(custody.CommandDomainControls):
    # Also retain the existing unframed-domain controls unchanged.
    def stream(self, request):
        return subprocess.Popen([os.environ['BL_CUSTODY_EXECUTOR'], '--custody-stream', json.dumps(request)],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def send(self, process, payload):
        process.stdin.write(struct.pack('>I', len(payload)) + payload)
        process.stdin.flush()

    def frame(self, process, timeout=8):
        deadline = time.monotonic() + timeout
        def exact(count):
            data = b''
            while len(data) < count:
                remaining = deadline - time.monotonic()
                self.assertGreater(remaining, 0, 'framed command observation deadline')
                self.assertTrue(select.select([process.stdout], [], [], remaining)[0], 'no command frame')
                chunk = os.read(process.stdout.fileno(), count-len(data))
                self.assertTrue(chunk, 'command wire ended without a terminal frame')
                data += chunk
            return data
        length = struct.unpack('>I', exact(4))[0]
        self.assertLessEqual(length, 8193)
        self.assertGreater(length, 0)
        payload = exact(length)
        return payload[0], payload[1:]

    def accepted(self, process):
        tag, payload = self.frame(process)
        self.assertEqual(1, tag)
        record = json.loads(payload)
        self.assertEqual('accepted', record['state'])
        self.assertTrue(record['unit'].startswith('bl-custody-'))
        return record

    def finish(self, root, process):
        if process.stdin and not process.stdin.closed:
            process.stdin.close()  # observation abandonment is not cancellation
        process.wait(timeout=12)
        for stream in [process.stdout,process.stderr]:
            if stream and not stream.closed:
                stream.close()
        self.assert_released(root)

    def test_output_needs_credit_but_completion_needs_no_extra_credit(self):
        with tempfile.TemporaryDirectory(prefix='command-credit-') as directory:
            root = Path(directory)
            process = self.stream(self.request(root, 'import os;os.write(1,b"hello");raise SystemExit(7)'))
            try:
                self.accepted(process)
                self.assertFalse(select.select([process.stdout], [], [], .15)[0])
                self.send(process, b'\x01' + struct.pack('>I', 1))
                self.assertEqual((2, b'hello'), self.frame(process))
                tag, payload = self.frame(process)
                self.assertEqual(3, tag)
                result = json.loads(payload)
                self.assertEqual('exited', result['state'])
                self.assertEqual(7, result['exitCode'])
                self.assertTrue(result['domainEmpty'])
                self.assertTrue(result['outputComplete'])
                self.assertEqual(7, process.wait(timeout=5))
            finally:
                self.finish(root, process)

    def test_a_paused_consumer_backpressures_the_os_writer_and_cancel_releases_every_loan(self):
        with tempfile.TemporaryDirectory(prefix='command-pressure-') as directory:
            root = Path(directory)
            program = ('import os,sys;from pathlib import Path;r=Path(sys.argv[1]);'
                       'r.joinpath("child").write_text(str(os.getpid()))\n'
                       'for n in range(8192):\n os.write(1,b"x"*8192)\n '
                       'r.joinpath("count.next").write_text(str(n+1))\n '
                       'os.replace(r/"count.next",r/"count")\n')
            process = self.stream(self.request(root, program, output=16777216))
            child = None
            try:
                self.accepted(process)
                child = self.wait_ready(root, process)
                time.sleep(.2)
                before = int((root/'count').read_text())
                time.sleep(.2)
                self.assertEqual(before, int((root/'count').read_text()), 'OS writer outran zero output demand')
                self.assertLess(before*8192, 1048576)
                self.send(process, b'\x02')
                tag, payload = self.frame(process)
                self.assertEqual(3, tag)
                result = json.loads(payload)
                self.assertEqual('cancelled', result['state'])
                self.assertTrue(result['domainEmpty'])
                self.assertFalse(result['outputComplete'])
                self.assertTrue(select.select([child], [], [], 1)[0])
            finally:
                self.finish(root, process)
                if child is not None:
                    os.close(child)

    def test_deadline_reports_a_stopped_new_session_orphan_without_output_demand(self):
        with tempfile.TemporaryDirectory(prefix='command-stream-deadline-') as directory:
            root = Path(directory)
            descendant = ('import os,signal,sys,time;from pathlib import Path;os.closerange(3,65536);'
                          'signal.signal(signal.SIGTERM,signal.SIG_IGN);'
                          'Path(sys.argv[1],"child").write_text(str(os.getpid()));time.sleep(30)')
            program = ('import subprocess,sys;subprocess.Popen([sys.executable,"-c",' + repr(descendant)
                       + ',sys.argv[1]],close_fds=True,start_new_session=True)')
            process = self.stream(self.request(root, program, timeout=700))
            child = None
            try:
                self.accepted(process)
                child = self.wait_ready(root, process)
                tag, payload = self.frame(process)
                self.assertEqual(3, tag)
                result = json.loads(payload)
                self.assertEqual('timed-out', result['state'])
                self.assertTrue(result['domainEmpty'])
                self.assertTrue(select.select([child], [], [], 1)[0])
            finally:
                self.finish(root, process)
                if child is not None:
                    os.close(child)

    def test_abandoned_observation_does_not_cancel_accepted_work(self):
        with tempfile.TemporaryDirectory(prefix='command-stream-abandon-') as directory:
            root = Path(directory)
            program = ('import os,sys,time;from pathlib import Path;r=Path(sys.argv[1]);'
                       'r.joinpath("child").write_text(str(os.getpid()));time.sleep(.7);r.joinpath("done").touch()')
            process = self.stream(self.request(root, program, timeout=5000))
            child = None
            try:
                self.accepted(process)
                child = self.wait_ready(root, process)
                process.stdin.close()
                process.stdout.close()
                with (root/'anchor').open('r+') as anchor:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(anchor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.assertEqual(0, process.wait(timeout=8))
                self.assertTrue((root/'done').exists())
                self.assertTrue(select.select([child], [], [], 1)[0])
            finally:
                self.finish(root, process)
                if child is not None:
                    os.close(child)

    def test_request_environment_cannot_redirect_the_command_manager(self):
        with tempfile.TemporaryDirectory(prefix='command-stream-manager-') as directory:
            root = Path(directory)
            request = self.request(root, 'from pathlib import Path;import sys;Path(sys.argv[1],"done").touch()')
            with patch.dict(os.environ, {'DBUS_SYSTEM_BUS_ADDRESS': 'unix:path=/missing/system-bus',
                                         'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/missing/user-bus',
                                         'XDG_RUNTIME_DIR': '/missing/runtime'}):
                process = self.stream(request)
            try:
                self.accepted(process)
                tag, payload = self.frame(process)
                self.assertEqual(3, tag)
                result = json.loads(payload)
                self.assertEqual(0, result['exitCode'])
                self.assertTrue((root/'done').exists())
            finally:
                self.finish(root, process)

    def test_private_binary_input_reaches_eof_without_entering_command_arguments(self):
        import hashlib
        for body in [b'', bytes(range(256))*4096]:
            with self.subTest(bytes=len(body)), tempfile.TemporaryDirectory(prefix='command-input-') as directory:
                root = Path(directory)
                request = self.request(root, 'import sys,hashlib;print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest(),end="")')
                request['input_bytes'] = len(body)
                process = self.stream(request)
                try:
                    self.send(process, b'\x04'+body)
                    self.send(process, b'\x01'+struct.pack('>I', 1))
                    self.accepted(process)
                    self.assertEqual((2, hashlib.sha256(body).hexdigest().encode()), self.frame(process))
                    tag, payload = self.frame(process)
                    self.assertEqual(3, tag)
                    self.assertEqual('exited', json.loads(payload)['state'])
                    self.assertEqual(0, process.wait(timeout=5))
                finally:
                    self.finish(root, process)

    def test_missing_input_expires_before_program_birth(self):
        with tempfile.TemporaryDirectory(prefix='command-input-expired-') as directory:
            root = Path(directory)
            request = self.request(root, 'from pathlib import Path;import sys;Path(sys.argv[1],"born").touch()', timeout=150)
            request['input_bytes'] = 100
            process = self.stream(request)
            try:
                tag, payload = self.frame(process)
                self.assertEqual(3, tag)
                self.assertEqual('unknown', json.loads(payload)['state'])
                self.assertEqual(125, process.wait(timeout=5))
                self.assertFalse((root/'born').exists())
            finally:
                self.finish(root, process)
