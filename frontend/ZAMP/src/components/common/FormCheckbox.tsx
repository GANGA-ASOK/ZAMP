import type { FC, ReactNode } from 'react';
import { Check } from '@phosphor-icons/react';

interface FormCheckboxProps {
  id?: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: ReactNode;
  required?: boolean;
  error?: string;
  className?: string;
}

export const FormCheckbox: FC<FormCheckboxProps> = ({
  id,
  checked,
  onChange,
  label,
  required = false,
  error,
  className = '',
}) => {
  const checkboxId = id || `checkbox-${Math.random().toString(36).substring(2, 9)}`;

  return (
    <div id={id ? `${id}-container` : undefined} className={`flex flex-col space-y-1 ${className}`}>
      <label htmlFor={checkboxId} className="flex items-start space-x-3 cursor-pointer group text-left">
        <div className="relative flex items-center justify-center shrink-0 mt-0.5">
          <input
            id={checkboxId}
            type="checkbox"
            checked={checked}
            onChange={(e) => onChange(e.target.checked)}
            className="sr-only"
          />
          <div
            className={`w-5 h-5 rounded-lg border transition-all duration-200 flex items-center justify-center ${
              checked
                ? 'bg-[#0875D1] border-[#0875D1] text-white shadow-xs'
                : error
                ? 'border-red-400 bg-red-50/50 group-hover:border-red-500'
                : 'border-slate-300 bg-white group-hover:border-slate-400'
            }`}
          >
            {checked && <Check size={14} weight="bold" />}
          </div>
        </div>

        <span className="text-sm text-slate-700 leading-snug select-none group-hover:text-slate-900 transition-colors">
          {label} {required && <span className="text-red-500 font-semibold">*</span>}
        </span>
      </label>

      {error && <p className="text-xs font-medium text-red-500 pl-8 animate-fadeIn">{error}</p>}
    </div>
  );
};
