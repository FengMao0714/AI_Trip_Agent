"use client";

import { useMemo, useState } from "react";
import { Check, Clipboard, Download, FileText } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  downloadTextFile,
  itineraryFilename,
  itineraryToMarkdown,
  itineraryToPlainText,
} from "@/lib/exportItinerary";
import type { Itinerary } from "@/types/itinerary";
import { cn } from "@/lib/utils";

interface ExportDialogProps {
  itinerary: Itinerary;
  triggerClassName?: string;
  triggerLabel?: string;
}

export function ExportDialog({
  itinerary,
  triggerClassName,
  triggerLabel = "导出",
}: ExportDialogProps) {
  const [copied, setCopied] = useState(false);
  const markdown = useMemo(() => itineraryToMarkdown(itinerary), [itinerary]);
  const plainText = useMemo(() => itineraryToPlainText(itinerary), [itinerary]);

  async function copyMarkdown() {
    if (!navigator.clipboard) {
      return;
    }

    await navigator.clipboard.writeText(markdown);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  function downloadMarkdown() {
    downloadTextFile(
      itineraryFilename(itinerary, "md"),
      markdown,
      "text/markdown;charset=utf-8",
    );
  }

  function downloadPlainText() {
    downloadTextFile(itineraryFilename(itinerary, "txt"), plainText);
  }

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className={cn(
            "rounded-lg border-amber-300/25 bg-amber-400/10 text-amber-100 hover:bg-amber-400/15 hover:text-amber-50",
            triggerClassName,
          )}
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[88vh] overflow-hidden rounded-lg border-white/10 bg-[#07100f] text-stone-100 shadow-2xl sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-amber-50">导出行程</DialogTitle>
        </DialogHeader>

        <div className="grid gap-2 sm:grid-cols-3">
          <Button
            type="button"
            variant="outline"
            className="rounded-lg border-white/10 bg-white/[0.04] text-stone-200 hover:bg-white/10 hover:text-stone-50"
            onClick={() => void copyMarkdown()}
          >
            {copied ? (
              <Check className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Clipboard className="h-4 w-4" aria-hidden="true" />
            )}
            {copied ? "已复制" : "复制 Markdown"}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="rounded-lg border-white/10 bg-white/[0.04] text-stone-200 hover:bg-white/10 hover:text-stone-50"
            onClick={downloadMarkdown}
          >
            <Download className="h-4 w-4" aria-hidden="true" />
            下载 Markdown
          </Button>
          <Button
            type="button"
            variant="outline"
            className="rounded-lg border-white/10 bg-white/[0.04] text-stone-200 hover:bg-white/10 hover:text-stone-50"
            onClick={downloadPlainText}
          >
            <FileText className="h-4 w-4" aria-hidden="true" />
            下载文本
          </Button>
        </div>

        <textarea
          readOnly
          aria-label="Markdown 预览"
          value={markdown}
          className="h-[46vh] resize-none rounded-lg border border-white/10 bg-black/35 p-3 font-mono text-xs leading-5 text-stone-300 outline-none"
        />
      </DialogContent>
    </Dialog>
  );
}
