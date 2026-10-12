import { useState } from "react";
import { Fish } from "lucide-react";

// Wave path that repeats every 1440 units, so the 200% strip loops seamlessly.
const WAVE_PATH_WIDE =
  "M0,96 C240,160 480,32 720,80 C960,128 1200,32 1440,96 C1680,160 1920,32 2160,80 C2400,128 2640,32 2880,96 L2880,160 L0,160 Z";

const WAVE_PATH_ORB =
  "M0,40 C240,80 480,0 720,30 C960,60 1200,0 1440,40 C1680,80 1920,0 2160,30 C2400,60 2640,0 2880,40 L2880,120 L0,120 Z";

export function AmbientBackground() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute -top-32 -left-24 h-[28rem] w-[28rem] rounded-full bg-tide-500/25 blur-3xl animate-float" />
      <div className="absolute top-1/3 -right-28 h-[32rem] w-[32rem] rounded-full bg-abyss-700/60 blur-3xl animate-float-slow" />
      <div className="absolute -bottom-40 left-1/4 h-[26rem] w-[26rem] rounded-full bg-tide-400/15 blur-3xl animate-float" />

      <svg
        className="absolute bottom-0 left-0 h-40 w-[200%] animate-wave text-tide-500/10"
        viewBox="0 0 2880 160"
        preserveAspectRatio="none"
      >
        <path fill="currentColor" d={WAVE_PATH_WIDE} />
      </svg>
    </div>
  );
}

export function BrandMark({ size = "md" }) {
  const isSmall = size === "sm";

  return (
    <div
      className={`grid shrink-0 place-items-center bg-linear-to-br from-tide-400 to-tide-600 text-abyss-950 shadow-lg shadow-tide-500/30 ${
        isSmall ? "h-9 w-9 rounded-xl" : "h-11 w-11 rounded-2xl"
      }`}
    >
      <Fish size={isSmall ? 18 : 22} strokeWidth={2.1} />
    </div>
  );
}

// A round "water level" badge: the wave sits inside the orb and drifts.
export function WaterOrb({ children }) {
  return (
    <div className="relative grid h-24 w-24 place-items-center overflow-hidden rounded-full border border-white/15 bg-abyss-800/70 shadow-[0_0_60px_-10px_rgb(43_192_201/0.45)]">
      <svg
        aria-hidden="true"
        className="absolute bottom-0 left-0 h-[62%] w-[200%] animate-wave text-tide-500/70"
        viewBox="0 0 2880 120"
        preserveAspectRatio="none"
      >
        <path fill="currentColor" d={WAVE_PATH_ORB} />
      </svg>
      <div className="relative z-10 text-foam-50">{children}</div>
    </div>
  );
}

// Full-bleed photo with a dark ocean wash on top so text stays readable.
// If the file is missing, the image hides itself and the background shows through.
export function PhotoBackdrop({ src, className = "" }) {
  return (
    <div aria-hidden="true" className={`pointer-events-none fixed inset-0 -z-20 overflow-hidden bg-abyss-950 ${className}`}>
      <img
        src={src}
        alt=""
        loading="eager"
        decoding="async"
        className="h-full w-full object-cover opacity-60"
        onError={(e) => {
          e.currentTarget.style.display = "none";
        }}
      />
      <div className="absolute inset-0 bg-linear-to-b from-abyss-950/70 via-abyss-900/75 to-abyss-950/95" />
    </div>
  );
}

// Wide photo banner for the chat's empty state. The logo badge overlaps its bottom edge.
export function PhotoBanner({ src, alt, children }) {
  return (
    <div className="relative w-full max-w-3xl overflow-visible">
      <div className="relative h-52 w-full overflow-hidden rounded-[2rem] border border-white/10 bg-linear-to-br from-abyss-700 to-abyss-900 sm:h-64">
        <img
          src={src}
          alt={alt}
          loading="eager"
          decoding="async"
          className="h-full w-full object-cover"
          onError={(e) => {
            e.currentTarget.style.display = "none";
          }}
        />
        <div className="absolute inset-0 bg-linear-to-t from-abyss-950/80 via-abyss-950/10 to-transparent" />
      </div>
      <div className="absolute -bottom-12 left-1/2 -translate-x-1/2">
        {children}
      </div>
    </div>
  );
}

// Veltris logo. Loads public/brand/veltris-logo.png when it exists.
// Until then it shows a plain text wordmark, so nothing breaks.

export function VeltrisLogo({ className = "h-14 w-21" }) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <span className="text-lg font-bold tracking-tight text-foam-50">
        veltris
      </span>
    );
  }

  return (
    <img
      src="/brand/veltris-logo.png"
      alt="Veltris"
      className={`shrink-0 object-contain ${className}`}
      onError={() => setFailed(true)}
    />
  );
}




export function VeltrisCredit({ className = "" }) {
  return (
    <div
      className={`flex items-center justify-center gap-0 text-xs text-foam-200/70 ${className}`}
    >
      <span className="whitespace-nowrap">A product of</span>
      <VeltrisLogo className="h-14 w-21 object-contain -ml-4" />
    </div>
  );
}

