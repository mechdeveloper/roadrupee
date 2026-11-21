"use client";

import { useEffect, useRef } from "react";
import { cssVar } from "@/lib/scale";
import { useReducedMotion } from "@/lib/useReducedMotion";

type Streak = { x: number; y: number; len: number; speed: number; alpha: number };

const COUNT = 60;
const FPS = 30;
const SLANT = 0.22; // horizontal drift per unit of vertical fall

/** Faint, slow rain behind the hero. Runs only while on screen and the tab is visible.
 *  Not rendered at all under prefers-reduced-motion. */
export function RainLayer() {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (reduced || !canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    let w = 0;
    let h = 0;
    let streaks: Streak[] = [];
    let raf = 0;
    let last = 0;
    let onScreen = true;
    const color = cssVar("--rain") || "rgba(60,80,105,0.08)";

    const seed = (): Streak => ({
      x: Math.random() * (w + h * SLANT) - h * SLANT,
      y: Math.random() * h,
      len: 14 + Math.random() * 22,
      speed: 90 + Math.random() * 110, // px per second: slow
      alpha: 0.5 + Math.random() * 0.5,
    });

    const resize = () => {
      const r = canvas.getBoundingClientRect();
      w = r.width;
      h = r.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      streaks = Array.from({ length: COUNT }, seed);
    };

    const frame = (t: number) => {
      raf = requestAnimationFrame(frame);
      if (t - last < 1000 / FPS) return;
      const dt = Math.min((t - last) / 1000, 0.1);
      last = t;
      ctx.clearRect(0, 0, w, h);
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      for (const s of streaks) {
        s.y += s.speed * dt;
        s.x += s.speed * dt * SLANT;
        if (s.y - s.len > h || s.x > w + 40) {
          s.y = -s.len;
          s.x = Math.random() * (w + h * SLANT) - h * SLANT;
        }
        ctx.globalAlpha = s.alpha;
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(s.x + s.len * SLANT, s.y + s.len);
        ctx.stroke();
      }
    };

    const update = () => {
      const shouldRun = onScreen && document.visibilityState === "visible";
      if (shouldRun && !raf) {
        last = performance.now();
        raf = requestAnimationFrame(frame);
        canvas.dataset.running = "true";
      } else if (!shouldRun && raf) {
        cancelAnimationFrame(raf);
        raf = 0;
        canvas.dataset.running = "false";
      }
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    const io = new IntersectionObserver(([e]) => {
      onScreen = e.isIntersecting;
      update();
    });
    io.observe(canvas);
    document.addEventListener("visibilitychange", update);
    update();

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
      document.removeEventListener("visibilitychange", update);
    };
  }, [reduced]);

  if (reduced) return null;
  return (
    <canvas
      ref={ref}
      aria-hidden
      data-running="false"
      className="pointer-events-none absolute inset-0 z-0 h-full w-full"
    />
  );
}
