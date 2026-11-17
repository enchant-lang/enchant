//! A credit wire over the existing OS command domain. No second supervisor.
//! Erlang ports use packet=4. Output requires credits; terminal metadata does
//! not. EOF abandons observation and drains accepted work under its OS budget.
use std::fs::File;
use std::io::{Read, Write};
use std::os::fd::AsRawFd;
use std::os::linux::net::SocketAddrExt;
use std::os::unix::net::{SocketAddr, UnixDatagram, UnixStream};
use std::path::Path;
use std::process::{Child, ExitStatus, Stdio};
use std::time::{Duration, Instant};
use serde_json::{json, Value};
use super::linux::control;

fn packet(tag: u8, bytes: &[u8]) -> std::io::Result<()> {
    let mut out = std::io::stdout().lock();
    out.write_all(&((bytes.len() + 1) as u32).to_be_bytes())?;
    out.write_all(&[tag])?;
    out.write_all(bytes)?;
    out.flush()
}

pub(super) fn unknown(error: &str) {
    let detail: String = error.chars().take(1024).collect();
    let _ = packet(3, json!({"state":"unknown","category":"command-domain-unconfirmed","detail":detail}).to_string().as_bytes());
}

pub(super) fn stop_command(executable: &Path, unit: &str, credential: &str) -> Result<String, String> {
    let path = executable.to_str().ok_or("command executor address is not UTF-8")?;
    if path.chars().any(char::is_control) { return Err("command executor address has control characters".into()); }
    let quote = |s: &str| format!("\"{}\"", s.replace('\\', "\\\\").replace('"', "\\\"").replace('%', "%%").replace('$', "$$"));
    Ok([quote(path), quote("--custody-result"), quote(unit), quote(credential)].join(" "))
}

pub(super) fn note(request: &Value, unit: &str, event: &str, data: Value) -> Result<(), String> {
    let Some(stream) = request.get("stream") else { return Ok(()) };
    let address = stream["address"].as_str().ok_or("missing private command address")?;
    let secret = stream["secret"].as_str().ok_or("missing private command nonce")?;
    let socket = UnixDatagram::unbound().map_err(|e| e.to_string())?;
    let address = SocketAddr::from_abstract_name(address.as_bytes()).map_err(|e| e.to_string())?;
    socket.connect_addr(&address).map_err(|e| e.to_string())?;
    socket.send(json!({"unit":unit,"secret":secret,"event":event,"data":data}).to_string().as_bytes())
        .map_err(|e| e.to_string())?;
    Ok(())
}

pub(super) fn stop_post(unit: &str, credential: &str) -> Result<i32, String> {
    let reply = control("systemctl")?.args(["--user","show","--value","--property=ControlPID",unit])
        .output().map_err(|e| e.to_string())?;
    if !reply.status.success() || String::from_utf8_lossy(&reply.stdout).trim() != std::process::id().to_string() {
        return Err("completion helper is not the OS domain's control process".into());
    }
    // systemd may already have removed the start credential directory during
    // ExecStopPost. The live launcher still holds the exact sealed memfd.
    let mut file=File::open(credential).map_err(|e| e.to_string())?;
    let required=libc::F_SEAL_SEAL|libc::F_SEAL_SHRINK|libc::F_SEAL_GROW|libc::F_SEAL_WRITE;
    let seals=unsafe {libc::fcntl(file.as_raw_fd(),libc::F_GET_SEALS)};
    if seals<0 || seals & required != required {
        return Err("completion credential is not sealed".into());
    }
    let mut bytes=Vec::new();
    (&mut file).take(1048577).read_to_end(&mut bytes).map_err(|e| e.to_string())?;
    if bytes.len()>1048576 {return Err("completion credential exceeds capacity".into());}
    let request: Value=serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
    note(&request,unit,"domain-stopped",json!({
        "result":std::env::var("SERVICE_RESULT").ok(),
        "exitCode":std::env::var("EXIT_CODE").ok(),
        "exitStatus":std::env::var("EXIT_STATUS").ok()
    }))?;
    Ok(0)
}

pub(super) struct Wire {
    receiver: UnixDatagram,
    address: String,
    secret: String,
}

impl Wire {
    pub(super) fn new(unit: &str) -> Result<Self,String> {
        let address = format!("bl-stream-{unit}");
        let mut random = [0u8;32];
        File::open("/dev/urandom").and_then(|mut file| file.read_exact(&mut random)).map_err(|e| e.to_string())?;
        let secret = crate::sha256_hex(&random);
        let socket = SocketAddr::from_abstract_name(address.as_bytes()).map_err(|e| e.to_string())?;
        let receiver = UnixDatagram::bind_addr(&socket).map_err(|e| e.to_string())?;
        receiver.set_nonblocking(true).map_err(|e| e.to_string())?;
        Ok(Self{receiver,address,secret})
    }

    pub(super) fn descriptor(&self) -> Value { json!({"address":self.address,"secret":self.secret}) }

    fn messages(&self,unit: &str) -> Vec<Value> {
        let mut messages = Vec::new();
        let mut bytes = [0u8;4096];
        // A bounded turn prevents a foreign local sender from starving I/O.
        for _ in 0..16 {
            match self.receiver.recv(&mut bytes) {
                Ok(n) => if let Ok(value) = serde_json::from_slice::<Value>(&bytes[..n]) {
                    if value["unit"] == unit && value["secret"] == self.secret { messages.push(value); }
                },
                Err(e) if e.kind()==std::io::ErrorKind::Interrupted => continue,
                Err(_) => break,
            }
        }
        messages
    }

    pub(super) fn run(&mut self,unit: &str,mut process: Child,mut output: UnixStream,maximum: u64) -> Result<i32,String> {
        let flags = unsafe { libc::fcntl(0,libc::F_GETFL) };
        if flags<0 || unsafe { libc::fcntl(0,libc::F_SETFL,flags|libc::O_NONBLOCK) }<0 { return Err("credit input unavailable".into()); }
        output.set_nonblocking(true).map_err(|e| e.to_string())?;
        let mut credits = 0u32;
        let mut input = Vec::new();
        let mut detached = false;
        let mut forwarding = true;
        let mut accepted = false;
        let mut eof = false;
        let mut count = 0u64;
        let mut discarded = 0u64;
        let mut forced: Option<&str> = None;
        let mut protocol_error = false;
        let mut program = None;
        let mut completion = None;
        let mut status: Option<ExitStatus> = None;
        let mut finished = None;
        loop {
            for message in self.messages(unit) {
                match message["event"].as_str() {
                    Some("accepted") if !accepted => {
                        accepted = true;
                        if forwarding && packet(1,json!({"unit":unit,"state":"accepted"}).to_string().as_bytes()).is_err() {
                            forwarding=false;detached=true;
                        }
                    },
                    Some("program-exited") => program=Some(message["data"].clone()),
                    Some("domain-stopped") => completion=Some(message["data"].clone()),
                    _ => {},
                }
            }
            if status.is_none() {
                status=process.try_wait().map_err(|e| e.to_string())?;
                if status.is_some() {finished=Some(Instant::now());}
            }
            // Terminal metadata is independent of output demand. Inspect EOF
            // without consuming a pending data byte when no credit remains.
            if !eof && !detached && credits==0 {
                let mut byte=0u8;
                if unsafe {libc::recv(output.as_raw_fd(), (&mut byte as *mut u8).cast(),1,libc::MSG_PEEK|libc::MSG_DONTWAIT)}==0 {eof=true;}
            }
            if completion.as_ref().is_some_and(|c|c["result"]=="timeout") {detached=true;}
            if status.is_some() && eof && (completion.is_some() || finished.is_some_and(|at|at.elapsed()>=Duration::from_millis(250))) {break;}
            let mut ready = [
                libc::pollfd{fd:if detached {-1}else{0},events:libc::POLLIN,revents:0},
                libc::pollfd{fd:if eof || (!detached && credits==0) {-1}else{output.as_raw_fd()},events:libc::POLLIN,revents:0},
                libc::pollfd{fd:self.receiver.as_raw_fd(),events:libc::POLLIN,revents:0},
            ];
            if unsafe { libc::poll(ready.as_mut_ptr(),ready.len() as _,100) }<0 {
                if std::io::Error::last_os_error().kind()==std::io::ErrorKind::Interrupted { continue; }
                return Err("command credit poll failed".into());
            }
            if ready[0].revents!=0 {
                let mut bytes=[0u8;64];
                match std::io::stdin().read(&mut bytes) {
                    Ok(0) => {detached=true;forwarding=false;},
                    Ok(n) => {
                        input.extend_from_slice(&bytes[..n]);
                        while input.len()>=4 {
                            let length=u32::from_be_bytes(input[..4].try_into().unwrap()) as usize;
                            if length==0 || length>5 {protocol_error=true;break;}
                            if input.len()<4+length {break;}
                            match &input[4..4+length] {
                                [1,a,b,c,d] => {
                                    let grant=u32::from_be_bytes([*a,*b,*c,*d]);
                                    if grant==0 || grant>64 || credits.saturating_add(grant)>64 {protocol_error=true;break;}
                                    credits+=grant;
                                },
                                [2] => {
                                    if control("systemctl")?.args(["--user","stop",unit]).stdout(Stdio::null()).stderr(Stdio::null())
                                        .status().map_err(|e| e.to_string())?.success() {
                                        forced=Some("cancelled");
                                        detached=true;
                                    }
                                },
                                [3] => {detached=true;forwarding=false;},
                                _ => {protocol_error=true;break;},
                            }
                            input.drain(..4+length);
                        }
                        if protocol_error {detached=true;forwarding=false;input.clear();}
                    },
                    Err(e) if matches!(e.kind(),std::io::ErrorKind::WouldBlock|std::io::ErrorKind::Interrupted) => {},
                    Err(_) => {detached=true;forwarding=false;},
                }
            }
            if ready[1].revents!=0 {
                let mut bytes=[0u8;8192];
                match output.read(&mut bytes) {
                    Ok(0) => eof=true,
                    Ok(n) => {
                        count+=n as u64;
                        if count>maximum && forced.is_none() {
                            let _=control("systemctl")?.args(["--user","stop",unit]).stdout(Stdio::null()).stderr(Stdio::null()).status();
                            forced=Some("output-limit");
                            detached=true;
                        }
                        if !detached {
                            credits-=1;
                            if forwarding && packet(2,&bytes[..n]).is_err() {forwarding=false;detached=true;}
                        } else {discarded+=n as u64;}
                    },
                    Err(e) if matches!(e.kind(),std::io::ErrorKind::WouldBlock|std::io::ErrorKind::Interrupted) => {},
                    Err(_) => return Err("command output stream failed".into()),
                }
            }
        }
        let service=completion.as_ref().and_then(|c| c["result"].as_str());
        let state=if protocol_error {"unknown"} else if let Some(reason)=forced {reason}
            else if service==Some("timeout") {"timed-out"}
            else if program.as_ref().is_some_and(|p| p["signal"].as_i64().is_some()) {"signalled"}
            else if matches!(service,Some("success"|"exit-code")) && program.as_ref().is_some_and(|p|
                p["code"].as_i64().is_some_and(|code|code!=0 || status.is_some_and(|s|s.success()))) {"exited"}
            else {"unknown"};
        let code=program.as_ref().and_then(|p|p["code"].as_i64());
        let result=json!({"state":state,"unit":unit,"accepted":accepted,"exitCode":code,
            "signal":program.as_ref().and_then(|p|p["signal"].as_i64()),"outputBytes":count,
            "discardedOutputBytes":discarded,"outputComplete":discarded==0,
            "domainEmpty":true,"serviceResult":service,"observerExitCode":status.and_then(|s|s.code())});
        if forwarding {let _=packet(3,result.to_string().as_bytes());}
        Ok(if state=="exited" {code.unwrap_or(125) as i32}else{125})
    }
}
