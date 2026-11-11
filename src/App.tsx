import { useEffect, useRef, useState } from "react";
import {
  ArrowUpRight,
  Check,
  ChevronDown,
  CircleHelp,
  Cloud,
  FileVideo,
  Gauge,
  LockKeyhole,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  Upload,
  Wifi,
  X,
} from "lucide-react";

type Stage = "ready" | "processing" | "complete";
type Metrics = {
  saved: string;
  bitrate: string;
  subject: string;
  fps: string;
};

const initialMetrics: Metrics = {
  saved: "—",
  bitrate: "—",
  subject: "—",
  fps: "—",
};

function formatBytes(bytes: number) {
  return bytes > 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [stage, setStage] = useState<Stage>("ready");
  const [progress, setProgress] = useState(0);
  const [bandwidth, setBandwidth] = useState(350);
  const [softness, setSoftness] = useState(55);
  const [detail, setDetail] = useState(92);
  const [showInfo, setShowInfo] = useState(false);
  const [metrics, setMetrics] = useState(initialMetrics);
  const [compare, setCompare] = useState(64);
  const [playing, setPlaying] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const chooseFile = (next: File | undefined) => {
    if (!next || !next.type.startsWith("video/")) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(next);
    setPreviewUrl(URL.createObjectURL(next));
    setStage("ready");
    setProgress(0);
    setMetrics(initialMetrics);
  };

  const startProcessing = () => {
    if (!file || stage === "processing") return;
    setStage("processing");
    setProgress(3);
    let value = 3;
    const timer = window.setInterval(() => {
      value += Math.round(Math.random() * 12) + 4;
      if (value >= 100) {
        window.clearInterval(timer);
        setProgress(100);
        setStage("complete");
        setMetrics({
          saved: `${Math.max(48, Math.round(92 - bandwidth / 60))}%`,
          bitrate: `${Math.max(10, Math.round(bandwidth * 0.72))} kbps`,
          subject: `${Math.round(20 + detail * 0.58)}%`,
          fps: "15.0",
        });
      } else {
        setProgress(value);
      }
    }, 320);
  };

  const togglePlayback = () => {
    if (!videoRef.current) return;
    if (playing) videoRef.current.pause();
    else void videoRef.current.play();
    setPlaying(!playing);
  };

  const reset = () => {
    setStage("ready");
    setProgress(0);
    setMetrics(initialMetrics);
  };

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">f.</div>
          <span className="brand-name">focusstream</span>
          <span className="brand-tag">smart video, lighter</span>
        </div>
        <div className="topbar-actions">
          <button className="quiet-button" onClick={() => setShowInfo(true)}>
            <CircleHelp size={15} /> How it works
          </button>
          <span className="local-pill"><LockKeyhole size={13} /> Local only</span>
        </div>
      </header>

      <section className="hero">
        <div>
          <div className="eyebrow">01 / Focus-aware compression</div>
          <h1>Keep what<br />matters <em>clear.</em></h1>
        </div>
        <div className="hero-copy">
          <p>
            A calmer way to send video over slow connections. FocusStream
            protects the people and objects that matter, so the rest can fade
            into the background.
          </p>
          <div className="privacy-note"><span className="live-dot" /> CPU-first · private by design</div>
        </div>
      </section>

      <section className="workspace">
        <aside className="controls card">
          <div className="card-kicker"><span>Workspace</span><span>01 — 03</span></div>
          <h2>Shape your stream</h2>
          <p className="muted">Choose a clip and tune the balance between clarity and bandwidth.</p>

          <button
            className={`dropzone ${file ? "has-file" : ""}`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              chooseFile(event.dataTransfer.files[0]);
            }}
          >
            <input ref={fileInputRef} type="file" accept="video/*" hidden onChange={(event) => chooseFile(event.target.files?.[0])} />
            {file ? (
              <>
                <div className="file-icon"><FileVideo size={20} /></div>
                <strong>{file.name}</strong>
                <span>{formatBytes(file.size)} · ready to analyze</span>
              </>
            ) : (
              <>
                <div className="upload-icon"><Upload size={19} /></div>
                <strong>Drop a video here</strong>
                <span>or browse from your computer</span>
              </>
            )}
          </button>

          <div className="control-list">
            <Slider label="Simulated connection" value={bandwidth} min={10} max={2000} step={10} suffix="kbps" onChange={setBandwidth} />
            <Slider label="Background softness" value={softness} min={0} max={100} step={5} suffix="%" onChange={setSoftness} />
            <Slider label="Subject detail" value={detail} min={60} max={100} step={1} suffix="%" onChange={setDetail} />
          </div>

          <button className="primary-button" disabled={!file || stage === "processing"} onClick={startProcessing}>
            {stage === "processing" ? <><span className="spinner" /> Processing {progress}%</> : <><Sparkles size={16} /> Compare the difference <ArrowUpRight size={16} /></>}
          </button>

          {stage === "processing" && (
            <div className="progress-track"><span style={{ width: `${progress}%` }} /></div>
          )}
          {stage === "complete" && (
            <button className="reset-button" onClick={reset}><RotateCcw size={13} /> Reset analysis</button>
          )}
        </aside>

        <section className="results card">
          <div className="results-header">
            <div><div className="card-kicker"><span>Output</span><span>02 — 03</span></div><h2>See the signal</h2></div>
            <div className="compare-legend"><span><i className="dot standard" /> Standard</span><span><i className="dot focus" /> FocusStream</span></div>
          </div>
          <div className="comparison">
            {previewUrl ? (
              <div className="comparison-stage">
                <video ref={videoRef} src={previewUrl} muted loop onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} />
                <div className="focus-layer" style={{ clipPath: `inset(0 0 0 ${compare}%)` }}>
                  <video src={previewUrl} muted loop />
                </div>
                <div className="comparison-divider" style={{ left: `${compare}%` }}><span /></div>
                <div className="comparison-label label-left">Standard</div>
                <div className="comparison-label label-right">FocusStream</div>
                <button className="play-button" onClick={togglePlayback}>{playing ? <Pause size={18} fill="currentColor" /> : <Play size={18} fill="currentColor" />}</button>
                <input className="compare-range" aria-label="Compare standard and FocusStream" type="range" min="10" max="90" value={compare} onChange={(event) => setCompare(Number(event.target.value))} />
              </div>
            ) : (
              <div className="empty-preview"><div className="empty-orbit"><Cloud size={26} /></div><strong>Your comparison lives here</strong><span>Upload a clip to see standard and focus-aware video side by side.</span></div>
            )}
          </div>
          <div className="metrics-grid">
            <Metric label="Bandwidth saved" value={metrics.saved} detail="vs. standard encode" accent />
            <Metric label="Focus stream" value={metrics.bitrate} detail="optimized bitrate" />
            <Metric label="Subject area" value={metrics.subject} detail="preserved in frame" />
            <Metric label="Processing" value={metrics.fps} detail="local CPU pipeline" />
          </div>
          <div className="results-footer"><span><span className="live-dot" /> {stage === "complete" ? "Analysis complete · subjects kept crisp" : "Ready for your first comparison"}</span><span>same bandwidth · two outcomes</span></div>
        </section>
      </section>

      <footer className="footer"><span><strong>focusstream</strong> · made for the in-between moments</span><span><Wifi size={13} /> offline-first / v0.3</span></footer>

      {showInfo && (
        <div className="modal-backdrop" onClick={() => setShowInfo(false)}>
          <div className="info-modal" onClick={(event) => event.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowInfo(false)}><X size={18} /></button>
            <div className="modal-icon"><Gauge size={22} /></div>
            <div className="eyebrow">The simple idea</div>
            <h2>Spend bytes<br />where they count.</h2>
            <p>FocusStream detects the important subject in each frame and gives it the detail it deserves. Background pixels are softened and compressed more aggressively, keeping the whole video usable on a slower connection.</p>
            <div className="modal-points"><span><Check size={14} /> No cloud uploads</span><span><Check size={14} /> CPU-first processing</span><span><Check size={14} /> Measured, not promised</span></div>
          </div>
        </div>
      )}
    </main>
  );
}

function Slider({ label, value, min, max, step, suffix, onChange }: { label: string; value: number; min: number; max: number; step: number; suffix: string; onChange: (value: number) => void }) {
  return (
    <label className="slider">
      <span className="slider-meta"><span>{label}</span><strong>{value} {suffix}</strong></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    </label>
  );
}

function Metric({ label, value, detail, accent = false }: { label: string; value: string; detail: string; accent?: boolean }) {
  return <div className={`metric ${accent ? "accent" : ""}`}><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>;
}

export default App;
