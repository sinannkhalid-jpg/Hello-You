"use client";
import { useEffect, useState } from "react";

export function Typewriter({
  words,
  typing = 60,
  pause = 1500,
  className,
}: {
  words: string[];
  typing?: number;
  pause?: number;
  className?: string;
}) {
  const [text, setText] = useState("");
  const [i, setI] = useState(0);
  const [j, setJ] = useState(0);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    const current = words[i % words.length];
    const t = setTimeout(() => {
      if (!deleting) {
        if (j < current.length) {
          setText(current.slice(0, j + 1));
          setJ(j + 1);
        } else {
          setTimeout(() => setDeleting(true), pause);
        }
      } else {
        if (j > 0) {
          setText(current.slice(0, j - 1));
          setJ(j - 1);
        } else {
          setDeleting(false);
          setI((i + 1) % words.length);
        }
      }
    }, deleting ? typing / 1.6 : typing);
    return () => clearTimeout(t);
  }, [j, deleting, i, words, typing, pause]);

  return <span className={className}>{text}<span className="animate-pulse text-cyan-300">|</span></span>;
}
