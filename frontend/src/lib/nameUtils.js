export function normalizeName(s) {
  if (s === null || s === undefined) return "";
  // Normalize to NFKD to decompose diacritics, then remove marks and punctuation.
  return String(s)
    .normalize("NFKD")
    .toLowerCase()
    .replace(/\p{M}/gu, "") // remove diacritic marks
  .replace(/[^\p{L}\p{N}\s]/gu, "") // remove punctuation but keep letters/numbers/spaces
    .replace(/\s+/g, " ")
    .trim();
}

export function encodeNameForUrl(s) {
  if (s === null || s === undefined) return "";
  return encodeURIComponent(String(s));
}

export function decodeNameFromUrl(s) {
  if (s === null || s === undefined) return "";
  try {
    return decodeURIComponent(String(s));
  } catch (e) {
    return String(s);
  }
}
