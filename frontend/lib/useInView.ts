"use client";

import { useEffect, useRef, useState } from "react";

/** Returns [ref, inView]. With `once`, stays true after the first time it is visible. */
export function useInView<T extends Element>(opts?: { once?: boolean; threshold?: number }) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);
  const once = opts?.once ?? false;
  const threshold = opts?.threshold ?? 0.3;

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setInView(true); // no observer: show everything
      return;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          if (once) io.disconnect();
        } else if (!once) {
          setInView(false);
        }
      },
      { threshold },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [once, threshold]);

  return [ref, inView] as const;
}
