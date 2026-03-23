import Papa from "papaparse";
import type { PriceChartingItem } from "@/types/product";
import { parsePrice } from "./pricing";

/**
 * Parse a PriceCharting CSV export into structured items.
 * Handles multiple column name variants that PriceCharting uses.
 * Ported from Python's load_pricecharting_csv()
 */
export function parsePriceChartingCSV(csvText: string): PriceChartingItem[] {
  const result = Papa.parse<Record<string, string>>(csvText, {
    header: true,
    skipEmptyLines: true,
    transformHeader: (header) => header.trim(),
  });

  const items: PriceChartingItem[] = [];

  for (const row of result.data) {
    const item: PriceChartingItem = {
      name: getField(row, ["product-name", "Product Name", "name"]).trim(),
      console: getField(row, ["console-name", "Console Name", "console"]).trim(),
      loosePrice: parsePrice(
        getField(row, ["loose-price", "Loose Price", "loose_price"])
      ),
      cibPrice: parsePrice(
        getField(row, ["cib-price", "CIB Price", "cib_price"])
      ),
      newPrice: parsePrice(
        getField(row, ["new-price", "New Price", "new_price"])
      ),
      upc: getField(row, ["upc", "UPC"]).trim(),
      asin: getField(row, ["asin", "ASIN"]).trim(),
    };

    // Only include items with a name and a positive loose price
    if (item.name && item.loosePrice > 0) {
      items.push(item);
    }
  }

  return items;
}

/**
 * Get a field value trying multiple possible column names.
 */
function getField(
  row: Record<string, string>,
  possibleKeys: string[]
): string {
  for (const key of possibleKeys) {
    if (row[key] !== undefined && row[key] !== null) {
      return row[key];
    }
  }
  return "";
}
