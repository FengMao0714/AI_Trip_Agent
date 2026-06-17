const KNOWLEDGE_AREAS = ["北京", "上海", "成都", "贵州", "贵阳"];
const LOCAL_KNOWLEDGE_RE = /本地知识库(?:推荐|检索)?(?:\s*[:：])?/;
const RAW_RAG_RE = /\brag_search\b|RAG\s*(?:推荐|检索)?/i;

function includesKnowledgeArea(text: string) {
  return KNOWLEDGE_AREAS.some((area) => text.includes(area));
}

function isRawRagText(text: string) {
  return RAW_RAG_RE.test(text);
}

function isLocalKnowledgeText(text: string) {
  return LOCAL_KNOWLEDGE_RE.test(text);
}

function hasSupportedRawRagRef(refs?: string[]) {
  return (refs ?? []).some((ref) => {
    const trimmed = ref.trim();
    return isRawRagText(trimmed) && includesKnowledgeArea(trimmed);
  });
}

export function hasTrustedKnowledgeSource(source?: string, refs?: string[]) {
  const sourceText = source?.trim() ?? "";
  const refText = (refs ?? []).join(" ");
  const combinedText = `${sourceText} ${refText}`;

  if (isLocalKnowledgeText(combinedText)) {
    return true;
  }

  if (isRawRagText(sourceText) || (refs ?? []).some(isRawRagText)) {
    return hasSupportedRawRagRef(refs) || includesKnowledgeArea(sourceText);
  }

  return false;
}

export function hasUnverifiedKnowledgeSource(source?: string, refs?: string[]) {
  const sourceText = source?.trim() ?? "";
  const hasRawRagClaim = isRawRagText(sourceText) || (refs ?? []).some(isRawRagText);

  if (!hasRawRagClaim) {
    return false;
  }

  return !hasTrustedKnowledgeSource(source, refs);
}

export function formatSourceLabel(source?: string, refs?: string[]) {
  if (!source?.trim()) {
    return "来源待确认";
  }

  const trimmed = source.trim();
  if (trimmed.includes("本地知识库") && !hasTrustedKnowledgeSource(trimmed, refs)) {
    return "知识库依据待核验";
  }

  if (isRawRagText(trimmed) && !hasTrustedKnowledgeSource(trimmed, refs)) {
    return "知识库依据待核验";
  }

  return source
    .replace(/RAG\s*推荐/gi, "本地知识库推荐")
    .replace(/RAG\s*检索/gi, "本地知识库检索")
    .replace(/\brag_search\b/gi, "本地知识库检索")
    .trim();
}

export function formatSourceRef(ref: string) {
  const trimmed = ref.trim();
  if (!trimmed) {
    return "";
  }

  const rawRagMatch = trimmed.match(/^rag_search\s*[:：]\s*(.*)$/i);
  if (rawRagMatch) {
    const query = rawRagMatch[1].trim();
    const label = includesKnowledgeArea(query)
      ? "本地知识库检索"
      : "知识库检索待核验";
    return query ? `${label}：${query}` : label;
  }

  const localKnowledgeMatch = trimmed.match(/^本地知识库检索\s*[:：]\s*(.*)$/i);
  if (localKnowledgeMatch) {
    const query = localKnowledgeMatch[1].trim();
    return query ? `本地知识库检索：${query}` : "本地知识库检索";
  }

  const localKnowledgeTitleMatch = trimmed.match(/^本地知识库\s*[:：]\s*(.*)$/i);
  if (localKnowledgeTitleMatch) {
    const title = localKnowledgeTitleMatch[1].trim();
    return title ? `本地知识库：${title}` : "本地知识库";
  }

  return trimmed
    .replace(/^rag_search\s*[:：]\s*/i, "本地知识库检索：")
    .replace(/^RAG\s*[:：]\s*/i, "本地知识库：")
    .replace(/RAG\s*推荐/gi, "本地知识库推荐")
    .replace(/RAG\s*检索/gi, "本地知识库检索")
    .replace(/\brag_search\b/gi, "本地知识库检索")
    .trim();
}

export function formatSourceRefs(refs?: string[], limit?: number) {
  const formatted = (refs ?? []).map(formatSourceRef).filter(Boolean);
  return typeof limit === "number" ? formatted.slice(0, limit) : formatted;
}

export function getKnowledgeSourceWarning(source?: string, refs?: string[]) {
  return hasUnverifiedKnowledgeSource(source, refs) ? "知识库依据待核验" : null;
}
