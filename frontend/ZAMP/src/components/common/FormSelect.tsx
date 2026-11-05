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
    <div className="w-full flex flex-col space-y-1.5 text-left">
      <label htmlFor={selectId} className="text-sm font-medium text-slate-700 flex items-center justify-between">
        <span>
          {label} {required && <span className="text-red-500 font-semibold">*</span>}
        </span>
        {!required && <span className="text-xs text-slate-400 font-normal">Optional</span>}
      </label>

      <div className="relative rounded-xl shadow-xs">
        <select
          id={selectId}
          value={value}
          className={`w-full appearance-none rounded-xl border bg-white px-3.5 py-2.5 pr-10 text-sm text-slate-800 transition-all duration-150 focus:outline-hidden focus:ring-2 ${
            !value ? 'text-slate-400' : 'text-slate-800'
          } ${
            error
              ? 'border-red-300 focus:border-red-500 focus:ring-red-200/50'
              : 'border-slate-200 hover:border-slate-300 focus:border-[#0875D1] focus:ring-[#0875D1]/20'
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
        <p className="text-xs font-medium text-red-500 animate-fadeIn">{error}</p>
      ) : helperText ? (
        <p className="text-xs text-slate-500">{helperText}</p>
      ) : null}
    </div>
  );
};
