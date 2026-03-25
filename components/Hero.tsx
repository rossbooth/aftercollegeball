'use client';

import { useEffect, useRef, useState } from 'react';

function AnimatedNumber({ end, duration = 2000 }: { end: number; duration?: number }) {
  const [val, setVal] = useState(end); // Start with final value for SSR
  const [mounted, setMounted] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);
  const started = useRef(false);

  useEffect(() => {
    setMounted(true);
    setVal(0); // Reset to 0 on client mount, then animate up
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const observer = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !started.current) {
        started.current = true;
        const t0 = performance.now();
        const tick = (now: number) => {
          const p = Math.min((now - t0) / duration, 1);
          const eased = 1 - Math.pow(1 - p, 3);
          setVal(Math.floor(eased * end));
          if (p < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      }
    }, { threshold: 0.3 });
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [end, duration, mounted]);

  return <span ref={ref}>{val.toLocaleString()}</span>;
}

export default function Hero() {
  return (
    <section className="relative overflow-hidden pt-16 pb-4 px-4 sm:px-6 md:pt-28 md:pb-4">
      {/* Background glow */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div
          className="absolute top-[20%] left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] rounded-full opacity-15 blur-[140px]"
          style={{ background: 'radial-gradient(circle, rgba(212,160,74,0.4) 0%, rgba(108,180,238,0.15) 50%, transparent 80%)' }}
        />
      </div>

      <div className="relative max-w-4xl mx-auto text-center">
        <h1
          className="text-4xl sm:text-5xl md:text-6xl lg:text-[5rem] font-bold tracking-tight leading-[1.08] opacity-0 animate-fade-in-up"
          style={{ color: '#e2e4f0' }}
        >
          What happens after<br className="sm:hidden" />{' '}
          <span className="relative inline-block">
            <span style={{
              background: 'linear-gradient(135deg, #d4a04a 0%, #e8c076 50%, #d4a04a 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>
              college ball
            </span>
            <span
              className="absolute -bottom-1 left-0 right-0 h-[3px] rounded-full"
              style={{ background: 'linear-gradient(90deg, #d4a04a, rgba(212,160,74,0.2))' }}
            />
          </span>
          ?
        </h1>

        <p
          className="mt-4 sm:mt-5 text-sm sm:text-base md:text-lg leading-relaxed opacity-0 animate-fade-in-up animate-delay-100 max-w-2xl mx-auto"
          style={{ color: '#6e7088' }}
        >
          We tracked{' '}<strong style={{ color: '#e2e4f0' }}><AnimatedNumber end={18688} /></strong>{' '}NCAA D1
          men&apos;s basketball players from 2015 to present.
          <br />
          Only{' '}<strong style={{ color: '#d4a04a' }}>1 in 22</strong>{' '}made the NBA. Here&apos;s where the rest ended up.
        </p>
      </div>
    </section>
  );
}
