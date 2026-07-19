import { ACTIVE_VERTICAL_ID } from "@/config/verticals";

const RAW_DATA_BASE_PATH =
  import.meta.env.VITE_DATA_BASE_PATH ?? `/data/${ACTIVE_VERTICAL_ID}`;
const TRIMMED = RAW_DATA_BASE_PATH.replace(/\/+$/, "");
export const DATA_BASE_PATH = TRIMMED.length > 0 ? TRIMMED : "/data";

/**
 * Build an absolute URL for a datasheet stored under the configured base path.
 */
export function dataUrl(relativePath: string): string {
  const sanitized = relativePath.replace(/^\/+/, "");
  return `${DATA_BASE_PATH}/${sanitized}`;
}
