import type { FC } from 'react';
import { useState } from 'react';
import { Eye, EyeSlash, Receipt, Bank, Info } from '@phosphor-icons/react';
import { FormInput } from '../components/common/FormInput';
import { FormSelect } from '../components/common/FormSelect';
import { FormCheckbox } from '../components/common/FormCheckbox';
import type {
  AccountType,
  FormValidationErrors,
  GSTStatus,
  TaxBankingInformationData,
} from '../types/vendor';
import { INDIAN_STATES } from '../utils/validation';
import { maskAccountNumber } from '../utils/formatters';

const GST_STATUS_OPTIONS: GSTStatus[] = ['Registered', 'Not Registered', 'Exempt'];
const ACCOUNT_TYPES: AccountType[] = ['Current Account', 'Savings Account', 'Other'];

interface Step3TaxBankingInfoProps {
  data: TaxBankingInformationData;
  errors: FormValidationErrors;
  onChange: (field: keyof TaxBankingInformationData, value: unknown) => void;
}

export const Step3TaxBankingInfo: FC<Step3TaxBankingInfoProps> = ({
  data,
  errors,
  onChange,
}) => {
  const [showAccountNo, setShowAccountNo] = useState(false);
  const [showConfirmAccountNo, setShowConfirmAccountNo] = useState(false);

  // Compute live embedded PAN mismatch indicator
  const pan = data.panNumber.trim().toUpperCase();
  const gstin = data.gstin.trim().toUpperCase();
  const isGstRegistered = data.gstStatus === 'Registered';
  const hasGstinPanMismatch =
    isGstRegistered &&
    pan.length === 10 &&
    gstin.length >= 12 &&
    gstin.substring(2, 12) !== pan;

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Card A: Tax Information */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-2xs hover:shadow-xs transition-shadow">
        <div className="flex items-center space-x-2.5 mb-4 pb-3 border-b border-slate-100">
          <div className="w-8 h-8 rounded-lg bg-sky-50 text-[#0875D1] flex items-center justify-center">
            <Receipt size={18} weight="bold" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-800">
              Tax Registration Details
            </h3>
            <p className="text-xs text-slate-500">
              Direct & indirect tax identifiers
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <FormInput
              label="PAN Number"
              required
              placeholder="e.g. ABCDE1234F"
              value={data.panNumber}
              onChange={(e) => onChange('panNumber', e.target.value.toUpperCase())}
              error={errors.panNumber}
              maxLength={10}
              helperText="10-digit Permanent Account Number"
            />
          </div>

          <div>
            <FormSelect
              label="GST Registration Status"
              required
              options={GST_STATUS_OPTIONS}
              value={data.gstStatus}
              onChange={(e) => onChange('gstStatus', e.target.value as GSTStatus)}
              error={errors.gstStatus}
            />
          </div>

          {isGstRegistered && (
            <>
              <div>
                <FormInput
                  label="GSTIN (Goods & Services Tax ID)"
                  required
                  placeholder="e.g. 29ABCDE1234F1Z5"
                  value={data.gstin}
                  onChange={(e) => onChange('gstin', e.target.value.toUpperCase())}
                  error={errors.gstin}
                  maxLength={15}
                  helperText={
                    hasGstinPanMismatch
                      ? '⚠️ Warning: Embedded PAN does not match PAN above'
                      : '15-character Goods and Services Tax Identification Number'
                  }
                />
              </div>

              <div>
                <FormSelect
                  label="GST Registration State"
                  required
                  placeholder="Select state"
                  options={INDIAN_STATES}
                  value={data.gstState}
                  onChange={(e) => onChange('gstState', e.target.value)}
                  error={errors.gstState}
                />
              </div>
            </>
          )}

          <div className={isGstRegistered ? 'sm:col-span-2' : ''}>
            <FormInput
              label="TAN Number"
              placeholder="e.g. ABCD12345E"
              value={data.tanNumber}
              onChange={(e) => onChange('tanNumber', e.target.value.toUpperCase())}
              error={errors.tanNumber}
              maxLength={10}
              helperText="Tax Deduction and Collection Account Number (if applicable)"
            />
          </div>
        </div>

        {/* Informative Disclaimer */}
        <div className="mt-4 flex items-start space-x-2 text-xs text-slate-500 bg-slate-50 p-3 rounded-xl border border-slate-100">
          <Info size={16} weight="bold" className="text-slate-400 mt-0.5 shrink-0" />
          <span>
            Format validation verifies correct syntax only. Official tax record verification will be conducted during the review stage.
          </span>
        </div>
      </div>

      {/* Card B: Banking Information */}
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 sm:p-6 shadow-2xs hover:shadow-xs transition-shadow">
        <div className="flex items-center space-x-2.5 mb-4 pb-3 border-b border-slate-100">
          <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <Bank size={18} weight="bold" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-800">
              Banking & Disbursement Details
            </h3>
            <p className="text-xs text-slate-500">
              Account used for payments and settlement
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <FormInput
              label="Account Holder Name"
              required
              placeholder="As per bank statement / passbook"
              value={data.accountHolderName}
              onChange={(e) => onChange('accountHolderName', e.target.value)}
              error={errors.accountHolderName}
            />
          </div>

          <div>
            <FormInput
              label="Bank Name"
              required
              placeholder="e.g. HDFC Bank, ICICI Bank"
              value={data.bankName}
              onChange={(e) => onChange('bankName', e.target.value)}
              error={errors.bankName}
            />
          </div>

          <div>
            <FormInput
              label="Branch Name"
              placeholder="e.g. Whitefield Branch"
              value={data.bankBranch}
              onChange={(e) => onChange('bankBranch', e.target.value)}
              error={errors.bankBranch}
            />
          </div>

          <div>
            <FormInput
              label="Bank Account Number"
              type={showAccountNo ? 'text' : 'password'}
              required
              placeholder="Enter bank account number"
              value={data.accountNumber}
              onChange={(e) => onChange('accountNumber', e.target.value.replace(/\D/g, ''))}
              error={errors.accountNumber}
              rightElement={
                <button
                  type="button"
                  onClick={() => setShowAccountNo(!showAccountNo)}
                  className="text-slate-400 hover:text-slate-600 cursor-pointer p-1"
                  aria-label={showAccountNo ? 'Hide account number' : 'Show account number'}
                >
                  {showAccountNo ? <EyeSlash size={16} /> : <Eye size={16} />}
                </button>
              }
            />
          </div>

          <div>
            <FormInput
              label="Confirm Bank Account Number"
              type={showConfirmAccountNo ? 'text' : 'password'}
              required
              placeholder="Re-enter bank account number"
              value={data.confirmAccountNumber}
              onChange={(e) => onChange('confirmAccountNumber', e.target.value.replace(/\D/g, ''))}
              error={errors.confirmAccountNumber}
              rightElement={
                <button
                  type="button"
                  onClick={() => setShowConfirmAccountNo(!showConfirmAccountNo)}
                  className="text-slate-400 hover:text-slate-600 cursor-pointer p-1"
                  aria-label={showConfirmAccountNo ? 'Hide account number' : 'Show account number'}
                >
                  {showConfirmAccountNo ? <EyeSlash size={16} /> : <Eye size={16} />}
                </button>
              }
            />
          </div>

          {/* Masked Preview if confirmed */}
          {data.accountNumber && data.accountNumber === data.confirmAccountNumber && (
            <div className="sm:col-span-2 px-3 py-2 rounded-xl bg-emerald-50/70 border border-emerald-200/60 flex items-center justify-between text-xs text-emerald-800">
              <span>Masked Account Display:</span>
              <span className="font-mono font-semibold tracking-wider">
                {maskAccountNumber(data.accountNumber)}
              </span>
            </div>
          )}

          <div>
            <FormInput
              label="IFSC Code"
              required
              placeholder="e.g. HDFC0001234"
              value={data.ifscCode}
              onChange={(e) => onChange('ifscCode', e.target.value.toUpperCase())}
              error={errors.ifscCode}
              maxLength={11}
              helperText="11-character Indian Financial System Code"
            />
          </div>

          <div>
            <FormSelect
              label="Account Type"
              required
              options={ACCOUNT_TYPES}
              value={data.accountType}
              onChange={(e) => onChange('accountType', e.target.value as AccountType)}
              error={errors.accountType}
            />
          </div>
        </div>

        {/* Bank Ownership Mandatory Checkbox */}
        <div className="mt-5 pt-4 border-t border-slate-100">
          <FormCheckbox
            id="confirm-bank-ownership"
            required
            checked={data.confirmBankOwnership}
            onChange={(checked) => onChange('confirmBankOwnership', checked)}
            label="I confirm that the provided bank account belongs to the registered business or its authorized proprietor."
            error={errors.confirmBankOwnership}
          />
        </div>
      </div>
    </div>
  );
};
