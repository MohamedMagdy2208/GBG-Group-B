import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";

type FieldShellProps = {
  label?: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  children: ReactNode;
};

export function Field({ label, hint, error, optional, children }: FieldShellProps) {
  return (
    <label className="block">
      {label ? (
        <span className="mb-1 flex items-center justify-between text-xs font-semibold text-ink-700">
          <span>{label}</span>
          {optional ? <span className="text-ink-400 font-normal">Optional</span> : null}
        </span>
      ) : null}
      {children}
      {error ? <p className="mt-1 text-xs text-danger-600">{error}</p> : hint ? <p className="mt-1 text-xs text-ink-500">{hint}</p> : null}
    </label>
  );
}

const INPUT_BASE =
  "block w-full rounded-2xl border border-ink-200 bg-white px-4 py-2.5 text-sm text-ink-900 placeholder:text-ink-400 transition focus:border-navy-500 focus:outline-none focus:ring-4 focus:ring-navy-500/10 disabled:bg-ink-50 disabled:text-ink-400";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  invalid?: boolean;
};

export const Input = forwardRef<HTMLInputElement, InputProps>(({ invalid, className = "", ...rest }, ref) => (
  <input
    ref={ref}
    {...rest}
    className={`${INPUT_BASE} ${invalid ? "border-danger-500 focus:border-danger-500 focus:ring-danger-500/15" : ""} ${className}`}
  />
));
Input.displayName = "Input";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  invalid?: boolean;
};

export const Select = forwardRef<HTMLSelectElement, SelectProps>(({ invalid, className = "", children, ...rest }, ref) => (
  <select
    ref={ref}
    {...rest}
    className={`${INPUT_BASE} cursor-pointer pr-10 appearance-none bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 20 20%22 fill=%22%2371788f%22><path fill-rule=%22evenodd%22 d=%22M5.23 7.21a.75.75 0 011.06.02L10 11.06l3.71-3.83a.75.75 0 111.08 1.04l-4.25 4.4a.75.75 0 01-1.08 0L5.21 8.27a.75.75 0 01.02-1.06z%22 clip-rule=%22evenodd%22 /></svg>')] bg-no-repeat bg-[right_0.75rem_center] bg-[length:1rem] ${invalid ? "border-danger-500" : ""} ${className}`}
  >
    {children}
  </select>
));
Select.displayName = "Select";

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  invalid?: boolean;
};

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(({ invalid, className = "", ...rest }, ref) => (
  <textarea
    ref={ref}
    {...rest}
    className={`${INPUT_BASE} min-h-[88px] resize-y ${invalid ? "border-danger-500 focus:border-danger-500 focus:ring-danger-500/15" : ""} ${className}`}
  />
));
Textarea.displayName = "Textarea";
