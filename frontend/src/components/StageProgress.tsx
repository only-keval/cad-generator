import { useEffect, useRef } from 'react';
import { RequestStatus } from '../api/types';

interface Props {
  status: RequestStatus | null;
  compact?: boolean;
  fullCard?: boolean;
}

function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const particles: { x: number; y: number; vx: number; vy: number; r: number; alpha: number }[] = [];
    const W = canvas.width = canvas.offsetWidth;
    const H = canvas.height = canvas.offsetHeight;

    for (let i = 0; i < 40; i++) {
      particles.push({
        x: Math.random() * W,
        y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4 - 0.2,
        r: Math.random() * 1.5 + 0.5,
        alpha: Math.random() * 0.5 + 0.1,
      });
    }

    let anim = true;
    const c = ctx!;
    function draw() {
      if (!anim) return;
      c.clearRect(0, 0, W, H);
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0) p.x = W;
        if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H;
        if (p.y > H) p.y = 0;
        c.beginPath();
        c.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        c.fillStyle = `rgba(124, 58, 237, ${p.alpha})`;
        c.fill();
      }
      requestAnimationFrame(draw);
    }
    draw();
    return () => { anim = false; };
  }, []);

  return <canvas ref={canvasRef} className="particle-canvas" />;
}

const STAGE_ICONS: Record<string, string> = {
  plan: '\u{1F9E0}',
  codegen: '\u26A1',
  execute: '\u{1F527}',
  fix: '\u{1F6E0}',
};

const STAGE_GRADIENTS: Record<string, [string, string]> = {
  plan: ['#7c3aed', '#a78bfa'],
  codegen: ['#2563eb', '#60a5fa'],
  execute: ['#059669', '#34d399'],
  fix: ['#ea580c', '#fb923c'],
};

export default function StageProgress({ status, compact, fullCard }: Props) {
  const stageName = status?.stage?.name;
  const attempt = status?.stage?.attempt ?? 0;
  const maxAttempts = status?.stage?.max_attempts ?? 5;

  if (!status && !compact) {
    return (
      <div className={`stage-progress full${fullCard ? ' overlay' : ''}`}>
        <div className="stage-hero">
          <div className="particle-layer">
            <ParticleCanvas />
          </div>
          <div className="stage-hero-content waiting-hero">
            <div className="orbital-ring">
              <div className="orbital-dot" />
              <div className="orbital-dot" />
              <div className="orbital-dot" />
            </div>
            <span className="stage-hero-label">Connecting to agent</span>
          </div>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="stage-progress compact">
        <div className="stage-compact-row">
          <div className="stage-compact-name">waiting</div>
        </div>
        <div className="stage-compact-bar waiting-bar" />
      </div>
    );
  }

  const displayStage = stageName || 'waiting';
  const gradient = STAGE_GRADIENTS[displayStage] || ['#7c3aed', '#a78bfa'];
  const icon = STAGE_ICONS[displayStage] || '\u23F3';

  if (compact) {
    return (
      <div className="stage-progress compact">
        <div className="stage-compact-row">
          <div className="stage-compact-name">{displayStage}</div>
          {attempt > 0 && (
            <div className="stage-compact-attempt">{attempt}/{maxAttempts}</div>
          )}
        </div>
        <div className="stage-compact-bar">
          <div
            className="stage-compact-fill"
            style={{
              width: attempt > 0 ? `${(attempt / maxAttempts) * 100}%` : '30%',
              background: `linear-gradient(90deg, ${gradient[0]}, ${gradient[1]})`,
            }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={`stage-progress full${fullCard ? ' overlay' : ''}`}>
      <div className="stage-hero">
        <div className="particle-layer">
          <ParticleCanvas />
        </div>
        <div className="stage-hero-content">
          <div className="stage-icon-ring" style={{ borderColor: gradient[1] }}>
            <span className="stage-icon">{icon}</span>
          </div>
          <span
            className="stage-hero-label"
            style={{
              backgroundImage: `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`,
            }}
          >
            {displayStage}
          </span>
          {attempt > 0 && (
            <span className="stage-hero-attempt" style={{ color: gradient[1] }}>
              attempt {attempt} of {maxAttempts}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
