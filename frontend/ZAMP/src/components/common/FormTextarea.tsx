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
    <div className="w-full flex flex-col space-y-1.5 text-left">
      <label htmlFor={textareaId} className="text-sm font-medium text-slate-700 flex items-center justify-between">
        <span>
          {label} {required && <span className="text-red-500 font-semibold">*</span>}
        </span>
        {!required && <span className="text-xs text-slate-400 font-normal">Optional</span>}
      </label>

      <div className="relative rounded-xl shadow-xs">
        <textarea
          id={textareaId}
          rows={rows}
          className={`w-full rounded-xl border bg-white px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 transition-all duration-150 focus:outline-hidden focus:ring-2 resize-y ${
            error
              ? 'border-red-300 focus:border-red-500 focus:ring-red-200/50'
              : 'border-slate-200 hover:border-slate-300 focus:border-[#0875D1] focus:ring-[#0875D1]/20'
          } ${className}`}
          {...props}
        />
      </div>

      {error ? (
        <p className="text-xs font-medium text-red-500 animate-fadeIn">{error}</p>
      ) : helperText ? (
        <p className="text-xs text-slate-500">{helperText}</p>
      ) : null}
    </div>
  );
};
