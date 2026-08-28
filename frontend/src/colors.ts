const PALETTE = [
  "#d32f2f",
  "#1976d2",
  "#2e7d32",
  "#ed6c02",
  "#7b1fa2",
  "#00838f",
  "#5d4037",
  "#546e7a",
  "#c2185b",
  "#388e3c",
  "#f9a825",
  "#6a1b9a",
];

const KNOWN_TYPES: Record<string, string> = {
  lek: "#1976d2",
  "klasa leków": "#0288d1",
  choroba: "#d32f2f",
  objaw: "#ed6c02",
  badanie: "#2e7d32",
  "czynnik ryzyka": "#7b1fa2",
  powikłanie: "#c2185b",
  procedura: "#00838f",
  "jednostka chorobowa": "#d32f2f",
};

export function colorForType(type: string | undefined): string {
  if (!type) {
    return "#757575";
  }
  const normalized = type.trim().toLowerCase();
  if (KNOWN_TYPES[normalized]) {
    return KNOWN_TYPES[normalized];
  }
  let hash = 0;
  for (let index = 0; index < normalized.length; index += 1) {
    hash = (hash * 31 + normalized.charCodeAt(index)) >>> 0;
  }
  return PALETTE[hash % PALETTE.length];
}
