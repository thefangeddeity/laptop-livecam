//! HTTPS for this node, configured on launch via `tailscale serve`.
//!
//! Not cosmetic. Browsers expose getUserMedia() only in a secure context,
//! so the two-way talk/roomaudio leg cannot reach a microphone over plain
//! HTTP. A node without HTTPS serves the viewer perfectly well and then
//! fails at RTC silently, which is the worst shape of broken -- nothing
//! looks wrong. Every other node in the fleet answers on
//! https://<node>.<tailnet>.ts.net; a fresh Windows install had no way to
//! get there without someone knowledgeable running a command by hand.
//!
//! `serve`, never `tailscale cert`: serve terminates TLS inside tailscaled
//! and never writes a certificate to disk, so renewal remains tailscaled's
//! problem. Of the file-based path Tailscale's own documentation says "you
//! are responsible for renewing the certificate", because the daemon
//! "doesn't know where to place a renewed certificate nor how to install
//! it". Automating that would trade a self-managing setup for one this
//! project owns forever, and would mask a renewal failure rather than
//! surface it.
//!
//! Shelling out to the CLI matches tailscale_ip() in routes.rs rather than
//! pulling in a binding for one call, and winproc::hidden stops a console
//! window flashing on every launch.

const CANDIDATES: [&str; 2] = ["tailscale", r"C:\Program Files\Tailscale\tailscale.exe"];

fn run(args: &[&str]) -> std::io::Result<std::process::Output> {
    let mut last: Option<std::io::Error> = None;
    for exe in CANDIDATES {
        match crate::winproc::hidden(exe).args(args).output() {
            Ok(out) => return Ok(out),
            Err(e) => last = Some(e),
        }
    }
    Err(last.unwrap_or_else(|| {
        std::io::Error::new(std::io::ErrorKind::NotFound, "tailscale CLI not found")
    }))
}

/// Point `https://<this node>/` at our own HTTP port.
///
/// Idempotent: Ok(false) when serve already proxies to that port, Ok(true)
/// when it was just configured. An Err is the caller's cue to log and keep
/// going -- Tailscale may be missing, stopped or logged out, and the node
/// still serves HTTP in that case. It must never be fatal: losing RTC is
/// bad, refusing to start at all is worse.
pub fn ensure_serving(port: u16) -> std::io::Result<bool> {
    let want = format!("http://127.0.0.1:{port}");
    if let Ok(status) = run(&["serve", "status"]) {
        if String::from_utf8_lossy(&status.stdout).contains(&want) {
            return Ok(false);
        }
    }
    let p = port.to_string();
    let out = run(&["serve", "--bg", &p])?;
    if out.status.success() {
        Ok(true)
    } else {
        Err(std::io::Error::other(format!(
            "`tailscale serve --bg {p}` failed: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        )))
    }
}

/// The port the viewer is actually bound to, read the same way main() reads
/// it, so serve can never be pointed at a port nothing is listening on.
pub fn bound_port() -> u16 {
    std::env::var("HLS_BIND")
        .ok()
        .and_then(|b| b.rsplit(':').next().and_then(|p| p.parse::<u16>().ok()))
        .unwrap_or(80)
}
