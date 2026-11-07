import type { FC, TextareaHTMLAttributes } from 'react';

interface FormTextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  error?: string;
  helperText?: string;
  required?: boolean;
}

export const FormTextarea: FC<FormTextareaProps> = ({
  label,
  error,
  helperText,
  required = false,
  id,
  className = '',
  rows = 3,
  ...props
}) => {
  const textareaId = id || label.toLowerCase().replace(/[^a-z0-9]/g, '-');

  return (
    <div className="w-full flex flex-col space-y-2 text-left">
      <label htmlFor={textareaId} className="text-[13px] font-medium text-slate-600 flex items-center justify-between px-1">
        <span>
          {label} {required && <span className="text-rose-500">*</span>}
        </span>
        {!required && <span className="text-[11px] text-slate-400 font-normal px-2 py-0.5 rounded-full border border-slate-200">Optional</span>}
      </label>

      <div className="relative rounded-2xl">
        <textarea
          id={textareaId}
          rows={rows}
          className={`w-full rounded-2xl border px-4 py-3 text-sm text-slate-800 placeholder-slate-400 transition-all duration-150 focus:outline-hidden focus:ring-2 resize-y ${
            error
              ? 'border-rose-300 bg-rose-50/60 focus:bg-white focus:border-rose-500 focus:ring-rose-200/60'
              : 'border-transparent bg-paper hover:bg-[#e7eae5] focus:bg-white focus:border-ink focus:ring-ink/10'
          } ${className}`}
          {...props}
        />
      </div>

      {error ? (
        <p className="text-xs font-medium text-rose-600 animate-fadeIn px-1">{error}</p>
      ) : helperText ? (
        <p className="text-xs text-slate-500 px-1">{helperText}</p>
      ) : null}
    </div>
  );
};
