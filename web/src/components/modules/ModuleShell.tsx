"use client";
import { ReactNode } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function ModuleShell({
  title, description, icon, input, run, loading, error, children, summary,
}: {
  title: string;
  description: string;
  icon: ReactNode;
  input: ReactNode;
  run: ReactNode;
  loading?: boolean;
  error?: any;
  children?: ReactNode;
  summary?: ReactNode;
}) {
  return (
    <div className="space-y-6">
      <PageHeader title={title} description={description} icon={icon} />
      <Card>
        <CardContent className="p-4 sm:p-5 flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">{input}</div>
          <div className="sm:w-auto">{run}</div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-rose-500/30">
          <CardContent className="p-5 text-sm text-rose-300">
            <p className="font-medium">Investigation failed</p>
            <p className="text-muted-foreground mt-1">{error?.message || "Unknown error"}</p>
          </CardContent>
        </Card>
      )}

      {loading && (
        <Card>
          <CardContent className="p-6 space-y-3">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-3 w-2/3" />
            <Skeleton className="h-32 w-full" />
          </CardContent>
        </Card>
      )}

      {summary}
      {children}
    </div>
  );
}
