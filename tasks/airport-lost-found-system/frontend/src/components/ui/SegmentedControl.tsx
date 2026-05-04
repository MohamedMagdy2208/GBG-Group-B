import type { ReactNode } from "react";

type Item<T extends string> = {
  value: T;
  label: ReactNode;
};

type Props<T extends string> = {
  value: T;
  options: Item<T>[];
  onChange: (value: T) => void;
  fullWidth?: boolean;
  size?: "sm" | "md";
  ariaLabel?: string;
};

export function SegmentedControl<T extends string>({ value, options, onChange, fullWidth, size = "md", ariaLabel }: Props<T>) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={`inline-flex items-center gap-1 rounded-2xl bg-ink-100 p-1 ring-1 ring-ink-200/60 ${fullWidth ? "w-full" : ""}`}
    >
      {options.map((option) => {
        const active = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(option.value)}
            className={`flex-1 rounded-xl px-3 ${size === "sm" ? "h-7 text-xs" : "h-8 text-[13px]"} font-semibold tracking-tight transition-all duration-150 ease-apple ${
              active
                ? "bg-white text-navy-800 shadow-card"
                : "text-ink-600 hover:text-ink-800"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
