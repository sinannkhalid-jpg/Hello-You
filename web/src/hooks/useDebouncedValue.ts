"use client";
import { useEffect, useState } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";

/** Sync `?target=` search-param ↔ local state, so module URLs are shareable. */
export function useTargetParam() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const initial = params.get("target") ?? "";
  const [target, setTarget] = useState(initial);
  useEffect(() => { setTarget(params.get("target") ?? ""); }, [params]);
  function set(t: string) {
    setTarget(t);
    const sp = new URLSearchParams(Array.from(params.entries()));
    if (t) sp.set("target", t); else sp.delete("target");
    router.replace(`${pathname}?${sp.toString()}`);
  }
  return { target, setTarget: set };
}
