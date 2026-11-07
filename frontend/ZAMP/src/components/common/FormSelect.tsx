import type { FC, SelectHTMLAttributes } from 'react';
import { CaretDown } from '@phosphor-icons/react';

interface Option {
  value: string;
  label: string;
}

interface FormSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: (string | Option)[];
  error?: string;
  helperText?: string;
  required?: boolean;
  placeholder?: string;
}

export const FormSelect: FC<FormSelectProps> = ({
  label,
  options,
  error,
  helperText,
  required = false,
  placeholder = 'Select an option',
  id,
  className = '',
  value,
  ...props
}) => {
  const selectId = id || label.toLowerCase().replace(/[^a-z0-9]/g, '-');

  return (
    <div className="w-full flex flex-col space-y-2 text-left">
      <label htmlFor={selectId} className="text-[13px] font-medium text-slate-600 flex items-center justify-between px-1">
        <span>
          {label} {required && <span className="text-rose-500">*</span>}
        </span>
        {!required && <span className="text-[11px] text-slate-400 font-normal px-2 py-0.5 rounded-full border border-slate-200">Optional</span>}
      </label>

      <div className="relative rounded-2xl">
        <select
          id={selectId}
          value={value}
          className={`w-full appearance-none rounded-2xl border px-4 py-3 pr-10 text-sm text-slate-800 transition-all duration-150 focus:outline-hidden focus:ring-2 ${
            !value ? 'text-slate-400' : 'text-slate-800'
          } ${
            error
              ? 'border-rose-300 bg-rose-50/60 focus:bg-white focus:border-rose-500 focus:ring-rose-200/60'
              : 'border-transparent bg-paper hover:bg-[#e7eae5] focus:bg-white focus:border-ink focus:ring-ink/10'
          } ${className}`}
          {...props}
        >
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options.map((opt) => {
            const val = typeof opt === 'string' ? opt : opt.value;
            const lbl = typeof opt === 'string' ? opt : opt.label;
            return (
              <option key={val} value={val} className="text-slate-800">
                {lbl}
              </option>
            );
          })}
        </select>

        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3.5 text-slate-400">
          <CaretDown size={18} weight="bold" />
        </div>
      </div>

      {error ? (
        <p className="text-xs font-medium text-rose-600 animate-fadeIn px-1">{error}</p>
      ) : helperText ? (
        <p className="text-xs text-slate-500 px-1">{helperText}</p>
      ) : null}
    </div>
  );
};
