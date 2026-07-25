"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Investigations } from "@/lib/api";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, Star, Trash2, Download, ArrowUpRight, FileText, FileSpreadsheet, FileJson } from "lucide-react";
import { ThreatChip } from "@/components/common/ThreatChip";
import { SkeletonList } from "@/components/common/SkeletonList";
import { EmptyState } from "@/components/common/EmptyState";
import { fmtRelative } from "@/lib/utils";
import { KIND_LABEL } from "@/components/layout/nav";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { Reports } from "@/lib/api";
import { getAccessToken } from "@/lib/api";

export default function SavedPage() {
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState<string>("all");
  const [fav, setFav] = useState<string>("all");

  const params: any = { limit: 100 };
  if (kind !== "all") params.kind = kind;
  if (fav === "yes") params.favorite = true;
  if (fav === "no") params.favorite = false;
  if (search) params.search = search;

  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["investigations", params],
    queryFn: () => Investigations.list(params),
  });

  const favM = useMutation({
    mutationFn: (id: string) => Investigations.favorite(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["investigations"] }),
  });
  const delM = useMutation({
    mutationFn: (id: string) => Investigations.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["investigations"] }); toast.success("Deleted"); },
  });

  function download(invId: string, fmt: "pdf" | "csv" | "json") {
    const url = Reports.exportUrl(invId, fmt);
    const token = getAccessToken();
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.blob())
      .then((b) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(b);
        a.download = `report.${fmt}`;
        a.click();
      });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Saved Investigations"
        description="Your full search history — filter, favorite, export, or delete."
      />

      <Card>
        <CardContent className="p-4 grid gap-3 sm:grid-cols-[1fr,180px,180px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#a1a1aa]" />
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search target…" className="pl-9" />
          </div>
          <Select value={kind} onValueChange={setKind}>
            <SelectTrigger><SelectValue placeholder="All kinds" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All kinds</SelectItem>
              {Object.entries(KIND_LABEL).map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={fav} onValueChange={setFav}>
            <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="yes">Favorites</SelectItem>
              <SelectItem value="no">Not favorited</SelectItem>
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {isLoading ? <SkeletonList rows={6} /> :
        !data || data.length === 0 ? (
          <EmptyState
            title="No investigations yet"
            description="Start an investigation from the sidebar. All your results will be saved here."
          />
        ) : (
          <Card>
            <CardContent className="p-0">
              <ul className="divide-y divide-[#262626]">
                {data.map((i: any) => (
                  <li key={i.id} className="p-4 flex items-center gap-3 hover:bg-[#1a1a1a] transition-colors">
                    <div className="min-w-0 flex-1">
                      <Link href={`/investigations/${i.id}`} className="font-medium hover:underline flex items-center gap-1.5">
                        {i.title || i.target}
                        <ArrowUpRight className="h-3.5 w-3.5 text-[#a1a1aa]" />
                      </Link>
                      <p className="text-xs text-[#a1a1aa]">
                        {(KIND_LABEL[i.kind] || i.kind)} · {fmtRelative(i.created_at)}
                      </p>
                    </div>
                    <ThreatChip level={i.threat_level} score={i.risk_score} />
                    <div className="flex items-center gap-1">
                      <Button size="icon" variant="ghost" onClick={() => favM.mutate(i.id)} aria-label="Favorite">
                        <Star className={`h-4 w-4 ${i.is_favorite ? "fill-white text-white" : "text-[#a1a1aa]"}`} />
                      </Button>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button size="icon" variant="ghost" aria-label="Export">
                            <Download className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                          <DropdownMenuItem onClick={() => download(i.id, "pdf")}><FileText className="h-4 w-4" /> PDF</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => download(i.id, "csv")}><FileSpreadsheet className="h-4 w-4" /> CSV</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => download(i.id, "json")}><FileJson className="h-4 w-4" /> JSON</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                      <Button size="icon" variant="ghost" onClick={() => delM.mutate(i.id)} aria-label="Delete">
                        <Trash2 className="h-4 w-4 text-[#a1a1aa]" />
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
    </div>
  );
}
