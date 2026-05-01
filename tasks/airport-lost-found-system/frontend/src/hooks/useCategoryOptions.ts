import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

type Category = {
  id: number;
  name: string;
};

const DEFAULT_CATEGORIES = [
  "Phone",
  "Laptop",
  "Bag",
  "Wallet",
  "Passport",
  "ID Card",
  "Headphones",
  "Keys",
  "Watch",
  "Clothing",
  "Electronics",
  "Tablet",
  "Camera",
  "Jewelry",
  "Documents",
  "Other",
];

export function useCategoryOptions() {
  const query = useQuery({
    queryKey: ["categories"],
    queryFn: async () => (await api.get<Category[]>("/categories")).data,
    staleTime: 5 * 60 * 1000,
  });

  const categories = useMemo(() => {
    const names = [...(query.data ?? []).map((category) => category.name), ...DEFAULT_CATEGORIES];
    const seen = new Set<string>();
    return names
      .map((name) => name.trim())
      .filter(Boolean)
      .filter((name) => {
        const key = name.toLowerCase();
        if (seen.has(key)) {
          return false;
        }
        seen.add(key);
        return true;
      });
  }, [query.data]);

  return { categories, isLoading: query.isLoading };
}
