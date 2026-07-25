"use client";
import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { Investigations } from "@/lib/api";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { CodeBlock } from "@/components/modules/KeyValueGrid";
import { ThreatChip } from "@/components/common/ThreatChip";
import { Skeleton } from "@/components/ui/skeleton";
import { fmtDate, fmtRelative } from "@/lib/utils";
import { KIND_LABEL } from "@/components/layout/nav";

export default function InvestigationDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, isLoading, error } = useQuery({
    queryKey: ["investigation", id],
    queryFn: () => Investigations.get(id),
  });

  if (error) {
    return <div className="text-sm text-[#ef4444]">Failed to load investigation.</div>;
  }
  if (isLoading || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-1/2" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={data.title || data.target}
        description={`${KIND_LABEL[data.kind] || data.kind} · ${fmtDate(data.created_at)}`}
        actions={<ThreatChip level={data.threat_level} score={data.risk_score} />}
      />
      <Card>
        <CardHeader>
          <CardTitle>Result</CardTitle>
          <CardDescription>Raw JSON returned by the OSINT module.</CardDescription>
        </CardHeader>
        <CardContent>
          <CodeBlock value={data.result} />
        </CardContent>
      </Card>
    </div>
  );
}
