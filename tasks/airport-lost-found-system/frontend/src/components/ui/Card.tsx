import type { HTMLAttributes, ReactNode } from "react";

type Props = HTMLAttributes<HTMLDivElement> & {
  as?: "div" | "section" | "article" | "aside";
  padded?: boolean;
  hover?: boolean;
  glass?: boolean;
};

export function Card({
  as: Tag = "div",
  padded = true,
  hover = false,
  glass = false,
  className = "",
  children,
  ...rest
}: Props) {
  const base = glass
    ? "glass border-white/40"
    : "bg-white border-ink-200/60";
  const hoverCls = hover
    ? "transition-all duration-200 ease-apple hover:shadow-card-hover hover:-translate-y-[1px]"
    : "transition-shadow duration-200";
  return (
    <Tag
      {...rest}
      className={`rounded-3xl border shadow-card ${base} ${hoverCls} ${padded ? "p-5" : ""} ${className}`}
    >
      {children}
    </Tag>
  );
}

export function CardHeader({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`mb-4 flex items-start justify-between gap-3 ${className}`}>{children}</div>;
}

export function CardTitle({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <h3 className={`text-base font-semibold tracking-tight text-ink-900 ${className}`}>{children}</h3>;
}

export function CardSubtitle({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`text-sm text-ink-500 ${className}`}>{children}</p>;
}
