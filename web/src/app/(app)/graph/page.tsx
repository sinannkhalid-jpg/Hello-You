"use client";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Osint } from "@/lib/api";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Share2, Database, Bookmark, Search, PlayCircle } from "lucide-react";
import { GraphCanvas } from "@/components/modules/GraphCanvas";
import { EmptyState } from "@/components/common/EmptyState";
import { CodeBlock } from "@/components/modules/KeyValueGrid";
import { fmtRelative } from "@/lib/utils";
import { toast } from "sonner";

const KINDS = [
  { v: "domain", l: "Domain" }, { v: "ip", l: "IP" }, { v: "email", l: "Email" },
  { v: "username", l: "Username" }, { v: "phone", l: "Phone" },
];

export default function GraphPage() {
  const [tab, setTab] = useState<"inv" | "manual">("inv");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Relationship Graph"
        description="Visualize the entities connected to your target."
        icon={<Share2 className="h-5 w-5" />}
      />
      <Tabs value={tab} onValueChange={(v) => setTab(v as any)}>
        <TabsList>
          <TabsTrigger value="inv"><Bookmark className="h-3.5 w-3.5" /> From saved investigation</TabsTrigger>
          <TabsTrigger value="manual"><Database className="h-3.5 w-3.5" /> Build from data</TabsTrigger>
        </TabsList>
        <TabsContent value="inv"><FromSaved /></TabsContent>
        <TabsContent value="manual"><ManualBuilder /></TabsContent>
      </Tabs>
    </div>
  );
}

function FromSaved() {
  const { data: invs } = useQuery({ queryKey: ["investigations", "all"], queryFn: () => import("@/lib/api").then((m) => m.Investigations.list({ limit: 100 })) });
  const [selected, setSelected] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["graph", selected],
    queryFn: () => Osint.graphFromInvestigation(selected!),
    enabled: !!selected,
  });

  return (
    <div className="grid gap-4 lg:grid-cols-[280px,1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Saved investigations</CardTitle>
          <CardDescription>Pick one to graph.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-1 max-h-[520px] overflow-y-auto">
          {(invs || []).length === 0 && (
            <p className="text-sm text-muted-foreground">Run an investigation first.</p>
          )}
          {(invs || []).map((i: any) => (
            <button
              key={i.id}
              onClick={() => setSelected(i.id)}
              className={`w-full text-left rounded-md px-3 py-2 text-sm transition-colors ${
                selected === i.id ? "bg-white/10" : "hover:bg-white/5"
              }`}
            >
              <div className="font-medium truncate">{i.title || i.target}</div>
              <div className="text-xs text-muted-foreground">{i.kind} · {fmtRelative(i.created_at)}</div>
            </button>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4">
          {isLoading ? <div className="text-sm text-muted-foreground p-8 text-center">Building graph…</div> :
            data ? <GraphCanvas nodes={data.nodes} edges={data.edges} /> :
            <EmptyState title="Pick an investigation" description="Select a saved investigation on the left to render its relationship graph." icon={<Share2 className="h-6 w-6" />} />}
        </CardContent>
      </Card>
    </div>
  );
}

function ManualBuilder() {
  const [kind, setKind] = useState("domain");
  const [target, setTarget] = useState("");
  const [context, setContext] = useState("");

  const mutation = useMutation({
    mutationFn: () => {
      let parsed: any = {};
      try { parsed = context.trim() ? JSON.parse(context) : {}; } catch { throw new Error("Context must be valid JSON"); }
      return Osint.graphFromData(kind, target, parsed);
    },
    onError: (e: any) => toast.error(e?.message || "Build failed"),
  });

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Build from data</CardTitle>
          <CardDescription>Paste a result object (e.g. from a domain or IP investigation).</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Label>Kind</Label>
            <Select value={kind} onValueChange={setKind}>
              <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
              <SelectContent>
                {KINDS.map((k) => <SelectItem key={k.v} value={k.v}>{k.l}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label>Target</Label>
            <Input className="mt-1.5" value={target} onChange={(e) => setTarget(e.target.value)} placeholder="example.com" />
          </div>
          <div>
            <Label>Data (JSON)</Label>
            <textarea
              value={context}
              onChange={(e) => setContext(e.target.value)}
              rows={10}
              className="mt-1.5 w-full rounded-md border border-white/10 bg-black/40 p-3 font-mono text-xs"
              placeholder='{ "dns": { "a": ["1.2.3.4"], "mx": [{ "priority": 10, "host": "mail…" }] } }'
            />
          </div>
          <Button onClick={() => mutation.mutate()} disabled={!target || mutation.isPending}>
            <PlayCircle className="h-4 w-4" /> Build graph
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-4">
          {mutation.data ? (
            <GraphCanvas nodes={mutation.data.nodes} edges={mutation.data.edges} />
          ) : (
            <EmptyState title="No graph yet" description="Provide target + JSON data and click Build graph." icon={<Search className="h-6 w-6" />} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
