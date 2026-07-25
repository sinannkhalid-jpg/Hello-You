"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/lib/auth";
import { Mail, Lock, Eye, EyeOff } from "lucide-react";
import { motion } from "framer-motion";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Min 8 characters"),
});
type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const { login, loading } = useAuth();
  const router = useRouter();
  const [show, setShow] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: FormData) {
    try {
      await login(values.email, values.password);
      toast.success("Welcome back");
      router.push("/dashboard");
    } catch (e: any) {
      toast.error(e?.message || "Invalid credentials");
    }
  }

  function onGoogle() {
    toast.info("Configure NEXT_PUBLIC_USE_SUPABASE=true to enable Google login.");
  }

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <h2 className="text-2xl font-semibold tracking-tight">Sign in</h2>
      <p className="text-sm text-[#a1a1aa] mt-1">Welcome back to Hello You.</p>

      <Button variant="secondary" className="w-full mt-6" onClick={onGoogle}>
        <GoogleIcon className="h-4 w-4" /> Continue with Google
      </Button>

      <div className="flex items-center gap-3 my-5">
        <Separator className="flex-1" />
        <span className="text-xs text-[#a1a1aa]">OR</span>
        <Separator className="flex-1" />
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="email">Email</Label>
          <div className="relative mt-1.5">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#a1a1aa]" />
            <Input id="email" type="email" autoComplete="email" className="pl-9"
                   {...register("email")} placeholder="you@example.com" />
          </div>
          {errors.email && <p className="text-xs text-[#ef4444] mt-1">{errors.email.message}</p>}
        </div>

        <div>
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link href="/forgot" className="text-xs text-white hover:underline">Forgot?</Link>
          </div>
          <div className="relative mt-1.5">
            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#a1a1aa]" />
            <Input id="password" type={show ? "text" : "password"} autoComplete="current-password" className="pl-9 pr-9"
                   {...register("password")} placeholder="••••••••" />
            <button type="button" onClick={() => setShow((s) => !s)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-[#a1a1aa] hover:text-white"
                    aria-label={show ? "Hide password" : "Show password"}>
              {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.password && <p className="text-xs text-[#ef4444] mt-1">{errors.password.message}</p>}
        </div>

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <p className="text-sm text-[#a1a1aa] mt-6 text-center">
        New to Hello You?{" "}
        <Link href="/register" className="text-white hover:underline">Create an account</Link>
      </p>
    </motion.div>
  );
}

function GoogleIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden>
      <path fill="#EA4335" d="M12 10.2v3.84h5.52c-.24 1.44-1.74 4.2-5.52 4.2-3.3 0-6-2.76-6-6.18s2.7-6.18 6-6.18c1.92 0 3.18.84 3.9 1.56l2.64-2.52C16.92 3.06 14.64 2.1 12 2.1 6.84 2.1 2.64 6.3 2.64 11.46S6.84 20.82 12 20.82c6.9 0 9.36-4.86 9.36-9.3 0-.66-.06-1.14-.12-1.62H12z" />
    </svg>
  );
}
