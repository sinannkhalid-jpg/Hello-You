"use client";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth";
import { Mail, ArrowLeft } from "lucide-react";
import { motion } from "framer-motion";

const schema = z.object({ email: z.string().email() });

export default function ForgotPage() {
  const { forgot } = useAuth();
  const [sent, setSent] = useState(false);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<{ email: string }>({
    resolver: zodResolver(schema),
  });

  async function onSubmit(v: { email: string }) {
    try {
      await forgot(v.email);
      setSent(true);
    } catch (e: any) {
      toast.error(e?.message || "Could not send reset email");
    }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <Link href="/login" className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3 w-3" /> Back to sign in
      </Link>
      <h2 className="mt-3 text-2xl font-semibold tracking-tight">Forgot password</h2>
      <p className="text-sm text-muted-foreground mt-1">We&apos;ll email you a reset link.</p>

      {sent ? (
        <div className="mt-6 glass rounded-xl p-5 text-sm">
          If an account exists for that email, a reset link has been sent.
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
          <div>
            <Label htmlFor="email">Email</Label>
            <div className="relative mt-1.5">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input id="email" type="email" className="pl-9" {...register("email")} placeholder="you@example.com" />
            </div>
            {errors.email && <p className="text-xs text-rose-400 mt-1">Enter a valid email</p>}
          </div>
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      )}
    </motion.div>
  );
}
