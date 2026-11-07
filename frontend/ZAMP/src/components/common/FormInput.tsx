import type { FC, InputHTMLAttributes, ReactNode } from 'react';

interface FormInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  helperText?: string;
  required?: boolean;
  leftIcon?: ReactNode;
  rightElement?: ReactNode;
}

export const FormInput: FC<FormInputProps> = ({
  label,
  error,
  helperText,
  required = false,
  leftIcon,
  rightElement,
  id,
  className = '',
  ...props
}) => {
  const inputId = id || label.toLowerCase().replace(/[^a-z0-9]/g, '-');

  return (
    <div className="w-full flex flex-col space-y-2 text-left">
      <label htmlFor={inputId} className="text-[13px] font-medium text-slate-600 flex items-center justify-between px-1">
        <span>
          {label} {required && <span className="text-rose-500">*</span>}
        </span>
        {!required && <span className="text-[11px] text-slate-400 font-normal px-2 py-0.5 rounded-full border border-slate-200">Optional</span>}
      </label>

      <div className="relative rounded-2xl">
        {leftIcon && (
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
            {leftIcon}
          </div>
        )}

        <input
          id={inputId}
          className={`w-full rounded-2xl border px-4 py-3 text-sm text-slate-800 placeholder-slate-400 transition-all duration-150 focus:outline-hidden focus:ring-2 ${
            leftIcon ? 'pl-10' : ''
          } ${rightElement ? 'pr-11' : ''} ${
            error
              ? 'border-rose-300 bg-rose-50/60 focus:bg-white focus:border-rose-500 focus:ring-rose-200/60'
              : 'border-transparent bg-paper hover:bg-[#e7eae5] focus:bg-white focus:border-ink focus:ring-ink/10'
          } ${className}`}
          {...props}
        />

        {rightElement && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
            {rightElement}
          </div>
        )}
      </div>

      {error ? (
        <p className="text-xs font-medium text-rose-600 animate-fadeIn px-1">{error}</p>
      ) : helperText ? (
        <p className="text-xs text-slate-500 px-1">{helperText}</p>
      ) : null}
    </div>
  );
};
