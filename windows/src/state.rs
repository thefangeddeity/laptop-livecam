//! Node state, persisted to disk.
//!
//! On Linux this state is spread across files owned by two different
//! processes (nginx serves broadcast.txt/buzz.txt straight off disk while
//! broadcast-api holds feed-mode and bw-mode in memory). None of that
//! split matters here -- what matters is that the observable GET results
//! are identical, so we keep one state dir and answer from it.
//!
//! Defaults are chosen to match a *fresh* Linux node:
//!   - message / buzz: empty (hls-livecam-setup seeds both files empty)
//!   - feed-mode: "show"
//!   - msg-lock: TRUE when no file exists (broadcast-api's FileNotFoundError arm)
//!   - bw-mode: false, and deliberately NOT persisted (matches broadcast-api,
//!     where _bw_mode is a plain global that resets when the service restarts)

use std::path::{Path, PathBuf};
use std::sync::Mutex;

use crate::audio_settings::AudioSettings;
use crate::notches::Notches;

pub struct AppState {
    dir: PathBuf,
    pub message: Mutex<String>,
    pub buzz: Mutex<String>,
    pub feed_mode: Mutex<String>,
    pub msg_lock: Mutex<bool>,
    pub dark: Mutex<bool>,
    /// In-memory only, by design. See module docs.
    pub bw_mode: Mutex<bool>,
    /// FORCE HLS -- pin every viewer to the HLS transport.
    ///
    /// NOT "turn HLS off", and not a fallback switch: the fallback is
    /// automatic and needs no setting. The opposite -- never negotiate
    /// WebRTC. One PeerConnection per viewer is held open for as long as
    /// they watch and this node pays for each; HLS is a directory of
    /// segments any number of people can pull without the node knowing
    /// they are there. Sub-second is the better trade for a household and
    /// the wrong one for an audience, so the choice can be made before the
    /// viewers arrive rather than discovered afterwards. It covers the room
    /// as well as the picture, because it is the same arithmetic.
    ///
    /// Persisted, and node-wide rather than per-viewer: the point is to
    /// protect the node, so one browser must not opt itself back onto the
    /// expensive path.
    pub force_hls: Mutex<bool>,
    /// LOW POWER -- one switch for a node that cannot keep up.
    ///
    /// Ported from the macOS branch, where it was measured: the CV render
    /// there took 62.7ms of a 66.7ms frame budget. This node is cheaper by
    /// construction -- CV is a read-only sidecar (cv.rs) rather than a
    /// render in the publish path -- so what it buys here is narrower and
    /// honest about it: the sidecar is not spawned (it is the ~130% of a
    /// core cv.rs's own module docs name) and the room-audio Opus leg is
    /// not kept alive.
    ///
    /// Persisted, unlike bw_mode: a node switched to low power because it
    /// could not cope must not come back from a reboot unable to cope
    /// again.
    pub low_power: Mutex<bool>,
    /// The notch-filter comb applied to the room-audio leg. Its own
    /// persistence (notches.json in this same state dir) -- see
    /// notches.rs module docs.
    pub notches: Notches,
    /// High-pass/low-pass/gain, persisted alongside the notches
    /// (audio.json) -- see audio_settings.rs module docs.
    pub audio: AudioSettings,
}

impl AppState {
    pub fn load() -> Self {
        let dir = state_dir();
        let _ = std::fs::create_dir_all(&dir);

        let notches = Notches::load(&dir);
        let audio = AudioSettings::load(&dir);
        let message = read(&dir, "broadcast.txt").unwrap_or_default();
        let buzz = read(&dir, "buzz.txt").unwrap_or_default();

        let feed_mode = match read(&dir, "feed_mode") {
            Some(m) if is_valid_mode(m.trim()) => m.trim().to_string(),
            _ => "show".to_string(),
        };

        // Absent lock file means locked, same as broadcast-api.
        let msg_lock = match read(&dir, "msg_lock") {
            Some(v) => v.trim() == "true",
            None => true,
        };

        // Absent means OFF, the opposite of msg_lock above: a node that
        // has never heard of this switch is a node nobody has asked to
        // give anything up.
        let low_power = matches!(read(&dir, "low_power"), Some(ref v) if v.trim() == "true");
        // Absent means OFF: a node nobody has prepared for an audience
        // should take the low-latency path.
        let force_hls = matches!(read(&dir, "force_hls"), Some(ref v) if v.trim() == "true");

        let dark = dir.join("dark").exists();

        Self {
            dir,
            message: Mutex::new(message),
            buzz: Mutex::new(buzz),
            feed_mode: Mutex::new(feed_mode),
            msg_lock: Mutex::new(msg_lock),
            dark: Mutex::new(dark),
            bw_mode: Mutex::new(false),
            low_power: Mutex::new(low_power),
            force_hls: Mutex::new(force_hls),
            notches,
            audio,
        }
    }

    pub fn dir(&self) -> &Path {
        &self.dir
    }

    pub fn set_message(&self, msg: &str) -> std::io::Result<()> {
        *self.message.lock().unwrap() = msg.to_string();
        std::fs::write(self.dir.join("broadcast.txt"), msg)
    }

    pub fn set_buzz(&self, ts: &str) -> std::io::Result<()> {
        *self.buzz.lock().unwrap() = ts.to_string();
        std::fs::write(self.dir.join("buzz.txt"), ts)
    }

    /// Shared by the HTTP `/api/buzz` handler and the GUI's Buzz button --
    /// one place generating the timestamp so both entry points produce the
    /// same observable result.
    pub fn buzz_now(&self) -> std::io::Result<String> {
        let ts = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_millis().to_string())
            .unwrap_or_else(|_| "0".to_string());
        self.set_buzz(&ts)?;
        Ok(ts)
    }

    pub fn set_feed_mode(&self, mode: &str) {
        *self.feed_mode.lock().unwrap() = mode.to_string();
        let _ = std::fs::write(self.dir.join("feed_mode"), mode);
    }

    pub fn toggle_msg_lock(&self) -> bool {
        let mut g = self.msg_lock.lock().unwrap();
        *g = !*g;
        let _ = std::fs::write(self.dir.join("msg_lock"), if *g { "true" } else { "false" });
        *g
    }

    pub fn force_hls(&self) -> bool {
        *self.force_hls.lock().unwrap()
    }

    pub fn set_force_hls(&self, on: bool) -> bool {
        *self.force_hls.lock().unwrap() = on;
        let _ = std::fs::write(self.dir.join("force_hls"), if on { "true" } else { "false" });
        on
    }

    pub fn low_power(&self) -> bool {
        *self.low_power.lock().unwrap()
    }

    pub fn set_low_power(&self, on: bool) -> bool {
        *self.low_power.lock().unwrap() = on;
        let _ = std::fs::write(self.dir.join("low_power"), if on { "true" } else { "false" });
        on
    }

    /// What the pipeline is ACTUALLY doing, which is not always what was
    /// asked. Low power cannot afford CV, so it is served as Show; the
    /// stored mode is left alone, so switching back needs no re-selection.
    /// Hide passes through untouched -- it is a privacy control, and
    /// already the cheapest branch there is.
    ///
    /// Every reader that gates on "is this node in CV mode" must come
    /// through here rather than reading feed_mode directly, or the sidecar
    /// starts anyway and the switch does nothing.
    pub fn effective_feed_mode(&self) -> String {
        let m = self.feed_mode.lock().unwrap().clone();
        if m == "cv" && self.low_power() { "show".to_string() } else { m }
    }

    pub fn toggle_bw_mode(&self) -> bool {
        let mut g = self.bw_mode.lock().unwrap();
        *g = !*g;
        *g
    }

    /// Linux represents dark as the mere existence of /var/lib/hls-livecam/dark,
    /// so create/remove the file rather than writing a value into it.
    pub fn toggle_dark(&self) -> bool {
        let mut g = self.dark.lock().unwrap();
        *g = !*g;
        let flag = self.dir.join("dark");
        if *g {
            let _ = std::fs::write(&flag, "");
        } else {
            let _ = std::fs::remove_file(&flag);
        }
        *g
    }

    /// A locally-placed cams.json wins, so this node can be promoted to
    /// aggregator later without a code change.
    pub fn cams_json(&self) -> String {
        read(&self.dir, "cams.json")
            .unwrap_or_else(|| crate::assets::CAMS_JSON_DEFAULT.to_string())
    }

    pub fn dark_png(&self) -> Option<Vec<u8>> {
        std::fs::read(self.dir.join("dark.png")).ok()
    }
}

pub fn is_valid_mode(m: &str) -> bool {
    matches!(m, "show" | "cloak" | "hide" | "cv")
}

fn read(dir: &Path, name: &str) -> Option<String> {
    std::fs::read_to_string(dir.join(name)).ok()
}

pub(crate) fn state_dir() -> PathBuf {
    if let Ok(d) = std::env::var("HLS_STATE_DIR") {
        return PathBuf::from(d);
    }
    match std::env::var("APPDATA") {
        Ok(appdata) => PathBuf::from(appdata).join("hls-livecam-win"),
        Err(_) => PathBuf::from(".hls-livecam-win"),
    }
}
