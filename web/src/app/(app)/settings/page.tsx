"use client";
import { useState } from "react";
import { Settings as SettingsApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Download, Trash2, KeyRound, Bell, Moon, Shield, User, LogOut, CheckCircle2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

export default function SettingsPage() {
  const router = useRouter();
  const { user, logout } = useAuth();

  const [dark, setDark] = useState(true);
  const [notif, setNotif] = useState(true);
  const [email, setEmail] = useState(false);
  const [apiKey, setApiKey] = useState("");

  async function exportData() {
    try {
      const data = await SettingsApi.export();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = data.filename || "account-export.json";
      a.click();
      toast.success("Exported");
    } catch (e: any) {
      toast.error(e?.message || "Export failed");
    }
  }

  async function deleteAccount() {
    if (!confirm("This will permanently delete your account. Continue?")) return;
    try {
      await SettingsApi.deleteAccount();
      await logout();
      toast.success("Account deleted");
      router.push("/");
    } catch (e: any) {
      toast.error(e?.message || "Delete failed");
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <PageHeader
        title="Settings"
        description="Preferences, security, data, and account controls."
        icon={<Shield className="h-5 w-5" />}
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><User className="h-4 w-4" /> Account</CardTitle>
          <CardDescription>{user?.email}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p><span className="text-muted-foreground">Name:</span> {user?.full_name || "—"}</p>
          <p><span className="text-muted-foreground">User ID:</span> <span className="font-mono text-xs">{user?.id}</span></p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Moon className="h-4 w-4" /> Appearance</CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Dark mode</p>
            <p className="text-xs text-muted-foreground">Cyberpunk theme is enabled by default.</p>
          </div>
          <Switch checked={dark} onCheckedChange={setDark} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Bell className="h-4 w-4" /> Notifications</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Row label="In-app notifications" description="Toasts and badges." value={notif} onChange={setNotif} />
          <Separator />
          <Row label="Email alerts" description="When a new investigation completes." value={email} onChange={setEmail} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><KeyRound className="h-4 w-4" /> API keys</CardTitle>
          <CardDescription>Set provider keys on the backend via .env. Browser-stored keys are optional.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label htmlFor="k">Have I Been Pwned (HIBP) — optional</Label>
            <Input id="k" className="mt-1.5" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="••••••••" />
            <p className="text-xs text-muted-foreground mt-1">Configure <code>HIBP_API_KEY</code> server-side for richer breach checks.</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Shield className="h-4 w-4" /> Security</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> Sessions encrypted in transit (HTTPS in prod).</p>
          <p className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> Bcrypt password hashing.</p>
          <p className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-emerald-400" /> Rate-limited API (60 req/min by default).</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Download className="h-4 w-4" /> Data</CardTitle>
          <CardDescription>Export or permanently delete your account.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button variant="ghost" onClick={exportData}><Download className="h-4 w-4" /> Export account (JSON)</Button>
          <Button variant="destructive" onClick={deleteAccount}><Trash2 className="h-4 w-4" /> Delete account</Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4">
          <Button variant="outline" onClick={async () => { await logout(); router.push("/login"); }}>
            <LogOut className="h-4 w-4" /> Sign out
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, description, value, onChange }: { label: string; description?: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
      <Switch checked={value} onCheckedChange={onChange} />
    </div>
  );
}
